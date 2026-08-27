from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any, cast

from acp import (
    PROTOCOL_VERSION,
    Agent,
    InitializeResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    run_agent,
    text_block,
    update_agent_message,
    update_user_message,
)
from acp.interfaces import Client
from acp.schema import (
    AgentCapabilities,
    Implementation,
    PermissionOption,
    PromptCapabilities,
    TextContentBlock,
    ToolCallProgress,
    ToolCallStart,
    ToolCallUpdate,
    ToolKind,
)

from nova import __version__
from nova.agent import NovaAgent


@dataclass
class _Session:
    agent: NovaAgent
    cancel_event: Event = field(default_factory=Event)
    prompt_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class NovaAcpAgent:
    def __init__(
        self,
        config: dict[str, Any],
        agent_factory: Callable[..., NovaAgent] = NovaAgent,
    ) -> None:
        self._config = config
        self._agent_factory = agent_factory
        self._client: Client | None = None
        self._sessions: dict[str, _Session] = {}

    def on_connect(self, conn: Client) -> None:
        self._client = conn

    async def initialize(self, protocol_version: int, **kwargs: Any) -> InitializeResponse:
        if protocol_version != PROTOCOL_VERSION:
            raise ValueError(
                f"Unsupported ACP protocol version {protocol_version}; "
                f"supported version is {PROTOCOL_VERSION}"
            )
        return InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(
                load_session=True,
                prompt_capabilities=PromptCapabilities(),
            ),
            agent_info=Implementation(name="nova-agent", version=__version__),
        )

    async def new_session(self, cwd: str, **kwargs: Any) -> NewSessionResponse:
        workspace = self._validate_workspace(cwd)
        agent = await asyncio.to_thread(
            self._agent_factory, config=copy.deepcopy(self._config), workspace=workspace
        )
        session_id = agent.session_id
        if not session_id:
            agent.close()
            raise RuntimeError("Nova did not create a session ID")
        agent._confirmation_callback = self._permission_callback(
            self._client, session_id, asyncio.get_running_loop()
        )
        self._sessions[session_id] = _Session(agent=agent)
        return NewSessionResponse(session_id=session_id)

    async def load_session(
        self,
        cwd: str,
        session_id: str,
        **kwargs: Any,
    ) -> LoadSessionResponse:
        workspace = self._validate_workspace(cwd)
        if self._client is None:
            raise RuntimeError("ACP client is not connected")
        if session_id not in self._sessions:
            try:
                agent = await asyncio.to_thread(
                    self._agent_factory,
                    config=copy.deepcopy(self._config),
                    session_id=session_id,
                    workspace=workspace,
                )
            except Exception as error:
                raise ValueError(f"Unknown Nova session: {session_id}") from error
            if agent.session_id != session_id:
                agent.close()
                raise ValueError(f"Unknown Nova session: {session_id}")
            agent._confirmation_callback = self._permission_callback(
                self._client, session_id, asyncio.get_running_loop()
            )
            self._sessions[session_id] = _Session(agent=agent)

        for message in self._sessions[session_id].agent.messages:
            content = message.get("content")
            if not isinstance(content, str) or not content:
                continue
            if message.get("role") == "user":
                await self._client.session_update(
                    session_id=session_id,
                    update=update_user_message(text_block(content)),
                )
            elif message.get("role") == "assistant":
                await self._client.session_update(
                    session_id=session_id,
                    update=update_agent_message(text_block(content)),
                )
            else:
                continue
        return LoadSessionResponse()

    async def prompt(
        self,
        session_id: str,
        prompt: list[Any],
        **kwargs: Any,
    ) -> PromptResponse:
        state = self._get_session(session_id)
        message = "".join(block.text for block in prompt if isinstance(block, TextContentBlock))
        if not message:
            raise ValueError("Nova ACP prompts require text content")
        if self._client is None:
            raise RuntimeError("ACP client is not connected")
        client = self._client

        async with state.prompt_lock:
            state.cancel_event.clear()
            state.agent._interrupt_check = state.cancel_event.is_set
            state.agent._tool_lifecycle_callback = self._tool_lifecycle_callback(
                client, session_id, loop=asyncio.get_running_loop()
            )
            loop = asyncio.get_running_loop()

            def stream_callback(chunk: str) -> None:
                update = update_agent_message(text_block(chunk))
                future = asyncio.run_coroutine_threadsafe(
                    client.session_update(session_id=session_id, update=update),
                    loop,
                )
                future.result()

            try:
                await asyncio.to_thread(
                    state.agent.run,
                    message,
                    stream=True,
                    stream_callback=stream_callback,
                )
            finally:
                state.agent._interrupt_check = None
                state.agent._tool_lifecycle_callback = None

            if state.cancel_event.is_set():
                return PromptResponse(stop_reason="cancelled")
            return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        self._get_session(session_id).cancel_event.set()

    def close(self) -> None:
        for state in self._sessions.values():
            state.agent.close()
        self._sessions.clear()

    def _tool_lifecycle_callback(
        self, client: Client, session_id: str, *, loop: asyncio.AbstractEventLoop
    ) -> Callable[[str, str, str, str | None], None]:
        def report(call_id: str, name: str, status: str, result: str | None) -> None:
            kind = self._tool_kind(name)
            if status == "start":
                update: Any = ToolCallStart(
                    tool_call_id=call_id,
                    title=name,
                    kind=kind,
                    status="pending",
                    session_update="tool_call",
                )
                progress: Any = ToolCallProgress(
                    tool_call_id=call_id,
                    kind=kind,
                    title=name,
                    status="in_progress",
                    session_update="tool_call_update",
                )
                for event in (update, progress):
                    future = asyncio.run_coroutine_threadsafe(
                        client.session_update(session_id=session_id, update=event), loop
                    )
                    future.result()
                return

            update = ToolCallProgress(
                tool_call_id=call_id,
                kind=kind,
                title=name,
                status=cast(Any, status),
                raw_output=result,
                session_update="tool_call_update",
            )
            future = asyncio.run_coroutine_threadsafe(
                client.session_update(session_id=session_id, update=update), loop
            )
            future.result()

        return report

    def _permission_callback(
        self, client: Client | None, session_id: str, loop: asyncio.AbstractEventLoop
    ) -> Callable[[str, dict[str, Any]], bool]:
        def request(name: str, arguments: dict[str, Any]) -> bool:
            if client is None or not callable(getattr(client, "request_permission", None)):
                return False
            tool_call = ToolCallUpdate(
                tool_call_id=f"permission-{session_id}",
                title=name,
                kind=self._tool_kind(name),
                raw_input=arguments,
                status="pending",
            )
            options = [
                PermissionOption(option_id="allow_once", name="Allow once", kind="allow_once"),
                PermissionOption(option_id="reject_once", name="Reject", kind="reject_once"),
            ]
            future = asyncio.run_coroutine_threadsafe(
                client.request_permission(session_id, tool_call, options), loop
            )
            try:
                response = future.result()
            except Exception:
                return False
            outcome = getattr(response, "outcome", None)
            return getattr(outcome, "option_id", None) == "allow_once"

        return request

    @staticmethod
    def _tool_kind(name: str) -> ToolKind:
        if name == "read_file":
            return "read"
        if name in {"write_file", "patch_file"}:
            return "edit"
        if name in {"search_files", "list_files"}:
            return "search"
        if name == "terminal":
            return "execute"
        if name in {"web_search", "http_request"} or name.startswith(("web_", "http_")):
            return "fetch"
        return "other"

    def _get_session(self, session_id: str) -> _Session:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise ValueError(f"Unknown ACP session: {session_id}") from error

    @staticmethod
    def _validate_workspace(cwd: str) -> Path:
        workspace = Path(cwd).expanduser()
        if not workspace.is_absolute() or not workspace.is_dir():
            raise ValueError("ACP cwd must be an existing absolute directory")
        return workspace.resolve()


async def run_acp_server(config: dict[str, Any]) -> None:
    adapter = NovaAcpAgent(config)
    try:
        await run_agent(cast(Agent, adapter))
    finally:
        adapter.close()
