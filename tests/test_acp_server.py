import asyncio
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from acp import text_block

from nova.acp_server import NovaAcpAgent


class StreamingAgent:
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.session_id = "test-session-id"
        self.messages: list[dict] = []
        self._interrupt_check = None
        self.closed = False

    def run(self, message: str, stream: bool, stream_callback) -> str:
        self.message = message
        self.stream = stream
        for chunk in self.chunks:
            stream_callback(chunk)
        return "".join(self.chunks)

    def close(self) -> None:
        self.closed = True


class LifecycleAgent(StreamingAgent):
    def __init__(self, events: list[tuple[str, str, str, str | None]]) -> None:
        super().__init__([])
        self.events = events

    def run(self, message: str, stream: bool, stream_callback) -> str:
        callback = getattr(self, "_tool_lifecycle_callback", None)
        assert callback is not None
        for event in self.events:
            callback(*event)
        return ""


@pytest.mark.asyncio
async def test_prompt_streams_updates_through_the_connected_client() -> None:
    nova_agent = StreamingAgent(["hello", " world"])
    factory = MagicMock(return_value=nova_agent)
    client = MagicMock()
    client.session_update = MagicMock(side_effect=lambda **kwargs: asyncio.sleep(0))
    adapter = NovaAcpAgent(config={"llm": {}}, agent_factory=factory)
    adapter.on_connect(client)

    initialized = await adapter.initialize(protocol_version=1)
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])
    response = await adapter.prompt(
        session_id=session.session_id,
        prompt=[text_block("say "), text_block("hello")],
    )

    assert initialized.protocol_version == 1
    assert initialized.agent_capabilities is not None
    assert initialized.agent_capabilities.load_session is True
    assert response.stop_reason == "end_turn"
    assert nova_agent.message == "say hello"
    assert nova_agent.stream is True
    assert [call.kwargs["session_id"] for call in client.session_update.call_args_list] == [
        session.session_id,
        session.session_id,
    ]
    assert [
        call.kwargs["update"].content.text for call in client.session_update.call_args_list
    ] == ["hello", " world"]


@pytest.mark.asyncio
async def test_prompt_reports_successful_tool_lifecycle_with_stable_id() -> None:
    agent = LifecycleAgent(
        [
            ("call-1", "read_file", "start", None),
            ("call-1", "read_file", "completed", "file contents"),
        ]
    )
    client = MagicMock()
    client.session_update = MagicMock(side_effect=lambda **kwargs: asyncio.sleep(0))
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock(return_value=agent))
    adapter.on_connect(client)
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    await adapter.prompt(session.session_id, [text_block("read it")])

    updates = [call.kwargs["update"] for call in client.session_update.call_args_list]
    assert [update.session_update for update in updates] == [
        "tool_call",
        "tool_call_update",
        "tool_call_update",
    ]
    assert [update.tool_call_id for update in updates] == ["call-1"] * 3
    assert updates[0].kind == "read"
    assert updates[1].status == "in_progress"
    assert updates[2].status == "completed"
    assert updates[2].raw_output == "file contents"


@pytest.mark.asyncio
async def test_prompt_reports_failed_tool_call() -> None:
    agent = LifecycleAgent(
        [("call-1", "terminal", "start", None), ("call-1", "terminal", "failed", "Error: denied")]
    )
    client = MagicMock()
    client.session_update = MagicMock(side_effect=lambda **kwargs: asyncio.sleep(0))
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock(return_value=agent))
    adapter.on_connect(client)
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    await adapter.prompt(session.session_id, [text_block("run it")])

    updates = [call.kwargs["update"] for call in client.session_update.call_args_list]
    assert updates[-1].status == "failed"
    assert updates[-1].kind == "execute"
    assert updates[-1].raw_output == "Error: denied"


@pytest.mark.asyncio
async def test_prompt_reports_multiple_calls_and_maps_tool_kinds() -> None:
    events = [
        ("read-id", "read_file", "start", None),
        ("read-id", "read_file", "completed", "ok"),
        ("edit-id", "patch_file", "start", None),
        ("edit-id", "patch_file", "completed", "ok"),
        ("search-id", "search_files", "start", None),
        ("search-id", "search_files", "completed", "ok"),
        ("fetch-id", "web_search", "start", None),
        ("fetch-id", "web_search", "completed", "ok"),
        ("other-id", "wiki", "start", None),
        ("other-id", "wiki", "completed", "ok"),
    ]
    agent = LifecycleAgent(events)
    client = MagicMock()
    client.session_update = MagicMock(side_effect=lambda **kwargs: asyncio.sleep(0))
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock(return_value=agent))
    adapter.on_connect(client)
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    await adapter.prompt(session.session_id, [text_block("tools")])

    updates = [call.kwargs["update"] for call in client.session_update.call_args_list]
    lifecycle = [update for update in updates if update.session_update != "agent_message_chunk"]
    assert [update.tool_call_id for update in lifecycle] == [
        "read-id",
        "read-id",
        "read-id",
        "edit-id",
        "edit-id",
        "edit-id",
        "search-id",
        "search-id",
        "search-id",
        "fetch-id",
        "fetch-id",
        "fetch-id",
        "other-id",
        "other-id",
        "other-id",
    ]
    assert [lifecycle[index].kind for index in (0, 3, 6, 9, 12)] == [
        "read",
        "edit",
        "search",
        "fetch",
        "other",
    ]


@pytest.mark.asyncio
async def test_prompt_reports_failed_cancelled_tool_call() -> None:
    started = threading.Event()
    released = threading.Event()

    class BlockingLifecycleAgent(LifecycleAgent):
        def run(self, message: str, stream: bool, stream_callback) -> str:
            callback = getattr(self, "_tool_lifecycle_callback", None)
            assert callback is not None
            callback("cancel-id", "write_file", "start", None)
            started.set()
            interrupt_check = self._interrupt_check
            assert interrupt_check is not None
            while not interrupt_check():
                released.wait(0.01)
            callback("cancel-id", "write_file", "failed", "[Interrupted]")
            return "[Interrupted]"

    agent = BlockingLifecycleAgent([])
    client = MagicMock()
    client.session_update = MagicMock(side_effect=lambda **kwargs: asyncio.sleep(0))
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock(return_value=agent))
    adapter.on_connect(client)
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    prompt_task = asyncio.create_task(adapter.prompt(session.session_id, [text_block("cancel")]))
    await asyncio.to_thread(started.wait, 1)
    await adapter.cancel(session.session_id)
    response = await asyncio.wait_for(prompt_task, timeout=1)
    released.set()

    updates = [call.kwargs["update"] for call in client.session_update.call_args_list]
    assert updates[-1].tool_call_id == "cancel-id"
    assert updates[-1].status == "failed"
    assert updates[-1].raw_output == "[Interrupted]"
    assert response.stop_reason == "cancelled"


@pytest.mark.asyncio
async def test_new_session_isolates_nova_agents(tmp_path) -> None:
    agents = [StreamingAgent([]), StreamingAgent([])]
    agents[0].session_id = "first-session"
    agents[1].session_id = "second-session"
    factory = MagicMock(side_effect=agents)
    adapter = NovaAcpAgent(config={"llm": {}}, agent_factory=factory)

    first_workspace = tmp_path / "one"
    second_workspace = tmp_path / "two"
    first_workspace.mkdir()
    second_workspace.mkdir()
    first = await adapter.new_session(cwd=str(first_workspace), mcp_servers=[])
    second = await adapter.new_session(cwd=str(second_workspace), mcp_servers=[])

    assert first.session_id != second.session_id
    assert factory.call_count == 2

    adapter.close()
    assert all(agent.closed for agent in agents)


@pytest.mark.asyncio
async def test_new_session_returns_the_nova_session_id() -> None:
    agent = StreamingAgent([])
    agent.session_id = "nova-session-id"
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock(return_value=agent))

    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    assert session.session_id == "nova-session-id"


@pytest.mark.asyncio
async def test_new_session_passes_absolute_workspace_to_nova(tmp_path) -> None:
    agent = StreamingAgent([])
    factory = MagicMock(return_value=agent)
    adapter = NovaAcpAgent(config={}, agent_factory=factory)

    await adapter.new_session(cwd=str(tmp_path), mcp_servers=[])

    factory.assert_called_once_with(config={}, workspace=tmp_path)


@pytest.mark.asyncio
async def test_new_session_rejects_relative_or_missing_workspace() -> None:
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock())

    with pytest.raises(ValueError, match="absolute directory"):
        await adapter.new_session(cwd="relative/path", mcp_servers=[])
    with pytest.raises(ValueError, match="absolute directory"):
        await adapter.new_session(cwd="/definitely/missing/nova-workspace", mcp_servers=[])


@pytest.mark.asyncio
async def test_cancel_interrupts_the_target_session() -> None:
    started = threading.Event()
    interrupted = threading.Event()

    class BlockingAgent(StreamingAgent):
        def run(self, message: str, stream: bool, stream_callback) -> str:
            started.set()
            assert self._interrupt_check is not None
            if self._interrupt_check():
                pytest.fail("interrupt was set before the prompt started")
            while not self._interrupt_check():
                interrupted.wait(0.01)
            interrupted.set()
            return ""

    adapter = NovaAcpAgent(
        config={},
        agent_factory=MagicMock(return_value=BlockingAgent([])),
    )
    adapter.on_connect(MagicMock())
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    prompt_task = asyncio.create_task(
        adapter.prompt(session_id=session.session_id, prompt=[text_block("wait")])
    )
    await asyncio.to_thread(started.wait, 1)
    await adapter.cancel(session_id=session.session_id)
    response = await asyncio.wait_for(prompt_task, timeout=1)

    assert interrupted.is_set()
    assert response.stop_reason == "cancelled"


@pytest.mark.asyncio
async def test_prompt_rejects_unknown_sessions() -> None:
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock())

    with pytest.raises(ValueError, match="Unknown ACP session"):
        await adapter.prompt(session_id="missing", prompt=[text_block("hello")])


@pytest.mark.asyncio
async def test_prompt_requires_text_content() -> None:
    adapter = NovaAcpAgent(config={}, agent_factory=MagicMock(return_value=StreamingAgent([])))
    session = await adapter.new_session(cwd="/tmp", mcp_servers=[])

    with pytest.raises(ValueError, match="text content"):
        await adapter.prompt(session_id=session.session_id, prompt=[])


@pytest.mark.asyncio
async def test_initialize_advertises_only_text_prompt_capabilities() -> None:
    adapter = NovaAcpAgent(config={})

    response = await adapter.initialize(protocol_version=1)

    capabilities = response.agent_capabilities
    assert capabilities is not None
    assert capabilities.load_session is True
    prompt_capabilities = capabilities.prompt_capabilities
    assert prompt_capabilities is not None
    assert prompt_capabilities.image is False
    assert prompt_capabilities.audio is False
    assert prompt_capabilities.embedded_context is False


@pytest.mark.asyncio
async def test_load_session_replays_user_and_agent_messages() -> None:
    agent = StreamingAgent([])
    agent.session_id = "stable-id"
    agent.messages = [
        {"role": "user", "content": "Question"},
        {"role": "assistant", "content": "Answer"},
        {"role": "tool", "content": "internal result"},
    ]
    factory = MagicMock(return_value=agent)
    client = MagicMock()
    client.session_update = MagicMock(side_effect=lambda **kwargs: asyncio.sleep(0))
    adapter = NovaAcpAgent(config={}, agent_factory=factory)
    adapter.on_connect(client)

    response = await adapter.load_session(
        cwd="/tmp",
        session_id="stable-id",
        mcp_servers=[],
    )

    assert response is not None
    factory.assert_called_once_with(
        config={},
        session_id="stable-id",
        workspace=Path("/tmp").resolve(),
    )
    assert [call.kwargs["session_id"] for call in client.session_update.call_args_list] == [
        "stable-id",
        "stable-id",
    ]
    assert [
        call.kwargs["update"].session_update for call in client.session_update.call_args_list
    ] == ["user_message_chunk", "agent_message_chunk"]
    assert [
        call.kwargs["update"].content.text for call in client.session_update.call_args_list
    ] == ["Question", "Answer"]


@pytest.mark.asyncio
async def test_load_session_rejects_unknown_session() -> None:
    factory = MagicMock(side_effect=ValueError("missing"))
    adapter = NovaAcpAgent(config={}, agent_factory=factory)
    adapter.on_connect(MagicMock())

    with pytest.raises(ValueError, match="Unknown Nova session"):
        await adapter.load_session(cwd="/tmp", session_id="missing", mcp_servers=[])
