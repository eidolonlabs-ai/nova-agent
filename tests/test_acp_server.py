import asyncio
import threading
from unittest.mock import MagicMock

import pytest
from acp import text_block

from nova.acp_server import NovaAcpAgent


class StreamingAgent:
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
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
    assert initialized.agent_capabilities.load_session is False
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
async def test_new_session_isolates_nova_agents() -> None:
    agents = [StreamingAgent([]), StreamingAgent([])]
    factory = MagicMock(side_effect=agents)
    adapter = NovaAcpAgent(config={"llm": {}}, agent_factory=factory)

    first = await adapter.new_session(cwd="/tmp/one", mcp_servers=[])
    second = await adapter.new_session(cwd="/tmp/two", mcp_servers=[])

    assert first.session_id != second.session_id
    assert factory.call_count == 2

    adapter.close()
    assert all(agent.closed for agent in agents)


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
    assert capabilities.load_session is False
    prompt_capabilities = capabilities.prompt_capabilities
    assert prompt_capabilities is not None
    assert prompt_capabilities.image is False
    assert prompt_capabilities.audio is False
    assert prompt_capabilities.embedded_context is False
