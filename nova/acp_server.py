from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Event
from typing import Any, cast

from acp import (
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
from acp.schema import AgentCapabilities, Implementation, PromptCapabilities, TextContentBlock

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
        return InitializeResponse(
            protocol_version=protocol_version,
            agent_capabilities=AgentCapabilities(
                load_session=True,
                prompt_capabilities=PromptCapabilities(),
            ),
            agent_info=Implementation(name="nova-agent", version=__version__),
        )

    async def new_session(self, cwd: str, **kwargs: Any) -> NewSessionResponse:
        agent = self._agent_factory(config=copy.deepcopy(self._config))
        session_id = agent.session_id
        if not session_id:
            agent.close()
            raise RuntimeError("Nova did not create a session ID")
        self._sessions[session_id] = _Session(agent=agent)
        return NewSessionResponse(session_id=session_id)

    async def load_session(
        self,
        cwd: str,
        session_id: str,
        **kwargs: Any,
    ) -> LoadSessionResponse:
        if self._client is None:
            raise RuntimeError("ACP client is not connected")
        if session_id not in self._sessions:
            try:
                agent = self._agent_factory(
                    config=copy.deepcopy(self._config),
                    session_id=session_id,
                )
            except Exception as error:
                raise ValueError(f"Unknown Nova session: {session_id}") from error
            if agent.session_id != session_id:
                agent.close()
                raise ValueError(f"Unknown Nova session: {session_id}")
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

            if state.cancel_event.is_set():
                return PromptResponse(stop_reason="cancelled")
            return PromptResponse(stop_reason="end_turn")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        self._get_session(session_id).cancel_event.set()

    def close(self) -> None:
        for state in self._sessions.values():
            state.agent.close()
        self._sessions.clear()

    def _get_session(self, session_id: str) -> _Session:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise ValueError(f"Unknown ACP session: {session_id}") from error


async def run_acp_server(config: dict[str, Any]) -> None:
    adapter = NovaAcpAgent(config)
    try:
        await run_agent(cast(Agent, adapter))
    finally:
        adapter.close()
