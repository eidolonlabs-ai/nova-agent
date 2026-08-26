"""Optional, failure-isolated Langfuse observability."""

from __future__ import annotations

import contextlib
import logging
import random
from collections.abc import Callable, Iterator
from typing import Any

logger = logging.getLogger(__name__)
_MAX_PREVIEW = 1000
_SECRET_KEYS = {"api_key", "secret_key", "password", "token", "authorization", "access_token"}


def redact(value: Any, *, limit: int = _MAX_PREVIEW) -> Any:
    """Return a bounded copy with common credential fields removed."""
    result: Any
    if isinstance(value, dict):
        result = {
            str(key): "[REDACTED]"
            if str(key).lower() in _SECRET_KEYS
            else redact(item, limit=limit)
            for key, item in value.items()
        }
    elif isinstance(value, (list, tuple)):
        result = [redact(item, limit=limit) for item in value]
    else:
        result = value
    if isinstance(result, str):
        return result[:limit]
    return result


def should_sample(rate: float, *, random_value: float | None = None) -> bool:
    """Choose whether a run is exported, without sampling SDK child events."""
    return rate > 0 and (
        rate >= 1 or (random_value if random_value is not None else random.random()) < rate
    )


class NoOpObservability:
    """Safe adapter used when telemetry is disabled or unavailable."""

    enabled = False

    @contextlib.contextmanager
    def run(self, run_id: str, goal: str, *, session_id: str | None = None) -> Iterator[None]:
        yield None

    def llm(
        self, model: str, *, input_data: Any = None, output_data: Any = None, **kwargs: Any
    ) -> None:
        return None

    def tool(
        self, name: str, *, input_data: Any = None, output_data: Any = None, **kwargs: Any
    ) -> None:
        return None

    def policy(self, name: str, *, allowed: bool, **kwargs: Any) -> None:
        return None

    def verification(self, name: str, *, status: str, **kwargs: Any) -> None:
        return None

    def shutdown(self) -> None:
        return None


class LangfuseObservability(NoOpObservability):
    enabled = True

    def __init__(self, config: dict[str, Any], client: Any) -> None:
        self.config = config
        self.client = client
        self._flushed = False

    def _payload(self, input_data: Any, output_data: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.config.get("capture_input", False):
            payload["input"] = redact(input_data)
        if self.config.get("capture_output", False):
            payload["output"] = redact(output_data)
        return payload

    @contextlib.contextmanager
    def _observation(self, kind: str, name: str, **kwargs: Any) -> Iterator[Any]:
        try:
            observation = self.client.start_as_current_observation(
                as_type="generation" if kind == "llm" else "span", name=name, **kwargs
            )
            enter = getattr(observation, "__enter__", None)
            current = enter() if callable(enter) else observation
        except Exception as exc:
            logger.warning("Langfuse observation failed: %s", type(exc).__name__)
            yield None
            return
        try:
            yield current
        finally:
            try:
                update = getattr(observation, "update", None)
                if callable(update):
                    update()
                exit_method = getattr(observation, "__exit__", None)
                if callable(exit_method):
                    exit_method(None, None, None)
                end = getattr(observation, "end", None)
                if callable(end):
                    end()
            except Exception as exc:
                logger.warning("Langfuse observation close failed: %s", type(exc).__name__)

    @contextlib.contextmanager
    def run(self, run_id: str, goal: str, *, session_id: str | None = None) -> Iterator[Any]:
        metadata = {"run_id": run_id}
        if session_id:
            metadata["session_id"] = session_id
        if self.config.get("environment"):
            metadata["environment"] = self.config["environment"]
        if self.config.get("release"):
            metadata["release"] = self.config["release"]
        payload = self._payload(goal, None)
        payload["metadata"] = metadata
        with self._observation("run", "nova.run", **payload) as observation:
            yield observation

    def _event(
        self, kind: str, name: str, input_data: Any = None, output_data: Any = None, **kwargs: Any
    ) -> None:
        payload = self._payload(input_data, output_data)
        payload["metadata"] = redact(kwargs)
        with self._observation(kind, name, **payload) as observation:
            if observation is not None:
                try:
                    update = getattr(observation, "update", None)
                    if callable(update):
                        update(**self._payload(input_data, output_data), metadata=redact(kwargs))
                except Exception as exc:
                    logger.warning("Langfuse observation update failed: %s", type(exc).__name__)

    def llm(
        self, model: str, *, input_data: Any = None, output_data: Any = None, **kwargs: Any
    ) -> None:
        self._event("llm", "nova.llm", input_data, output_data, model=model, **kwargs)

    def tool(
        self, name: str, *, input_data: Any = None, output_data: Any = None, **kwargs: Any
    ) -> None:
        self._event("tool", "nova.tool", input_data, output_data, tool_name=name, **kwargs)

    def policy(self, name: str, *, allowed: bool, **kwargs: Any) -> None:
        self._event("policy", "nova.policy", allowed=allowed, tool_name=name, **kwargs)

    def verification(self, name: str, *, status: str, **kwargs: Any) -> None:
        self._event("verification", "nova.verification", status=status, tool_name=name, **kwargs)

    def shutdown(self) -> None:
        if self._flushed or not self.config.get("flush_at_shutdown", True):
            return
        self._flushed = True
        try:
            self.client.flush()
        except Exception as exc:
            logger.warning("Langfuse flush failed: %s", type(exc).__name__)


def create_observability(
    config: dict[str, Any], *, client_factory: Callable[[dict[str, Any]], Any] | None = None
) -> NoOpObservability | LangfuseObservability:
    """Build telemetry lazily; importing/initializing the SDK is best effort."""
    settings = config.get("observability", {})
    if (
        not isinstance(settings, dict)
        or not settings.get("enabled")
        or settings.get("provider", "langfuse") != "langfuse"
    ):
        return NoOpObservability()
    rate = settings.get("sample_rate", 1.0)
    if not should_sample(float(rate)):
        return NoOpObservability()
    langfuse_config = dict(settings.get("langfuse", {}))
    langfuse_config.setdefault("base_url", "https://cloud.langfuse.com")
    if client_factory is not None:
        try:
            return LangfuseObservability(settings, client_factory(langfuse_config))
        except Exception as exc:
            logger.warning("Langfuse initialization failed: %s", type(exc).__name__)
            return NoOpObservability()
    try:
        from langfuse import Langfuse

        public_key = langfuse_config.get("public_key")
        secret_key = langfuse_config.get("secret_key")
        if not public_key or not secret_key:
            return NoOpObservability()
        client = Langfuse(
            public_key=public_key, secret_key=secret_key, host=langfuse_config["base_url"]
        )
        return LangfuseObservability(settings, client)
    except Exception as exc:
        logger.warning("Langfuse initialization failed: %s", type(exc).__name__)
        return NoOpObservability()
