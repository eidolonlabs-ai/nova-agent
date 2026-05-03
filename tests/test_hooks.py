"""Tests for the hook/callback system."""

from nova.hooks import (
    ALL_EVENTS,
    EVENT_POST_LLM_CALL,
    EVENT_POST_TOOL_CALL,
    EVENT_PRE_LLM_CALL,
    EVENT_PRE_TOOL_CALL,
    EVENT_SESSION_END,
    EVENT_SESSION_START,
    HookRegistry,
    hooks,
)

# ── Event Constants ─────────────────────────────────────────────────────────


def test_all_events_defined():
    assert EVENT_PRE_TOOL_CALL in ALL_EVENTS
    assert EVENT_POST_TOOL_CALL in ALL_EVENTS
    assert EVENT_PRE_LLM_CALL in ALL_EVENTS
    assert EVENT_POST_LLM_CALL in ALL_EVENTS
    assert EVENT_SESSION_START in ALL_EVENTS
    assert EVENT_SESSION_END in ALL_EVENTS


# ── HookRegistry — Basic Operations ─────────────────────────────────────────


def test_register_and_emit():
    registry = HookRegistry()
    results = []

    registry.on("pre_tool_call", lambda tool_name, **kw: results.append(tool_name))
    registry.emit("pre_tool_call", tool_name="terminal", args={"command": "ls"})

    assert results == ["terminal"]


def test_multiple_callbacks():
    registry = HookRegistry()
    results = []

    registry.on("pre_tool_call", lambda tool_name, **kw: results.append(f"1:{tool_name}"))
    registry.on("pre_tool_call", lambda tool_name, **kw: results.append(f"2:{tool_name}"))
    registry.emit("pre_tool_call", tool_name="read_file")

    assert results == ["1:read_file", "2:read_file"]


def test_callback_return_values():
    registry = HookRegistry()
    registry.on("post_tool_call", lambda result, **kw: result.upper())
    results = registry.emit("post_tool_call", result="hello")
    assert results == ["HELLO"]


def test_callback_error_does_not_break_others():
    registry = HookRegistry()
    results = []

    def bad_callback(**kw):
        raise ValueError("boom")

    registry.on("pre_tool_call", bad_callback)
    registry.on("pre_tool_call", lambda **kw: results.append("ok"))

    # Should not raise — errors are caught
    registry.emit("pre_tool_call", tool_name="test")
    assert results == ["ok"]


def test_remove_callback():
    registry = HookRegistry()
    results = []
    cb = lambda **kw: results.append(1)  # noqa: E731

    registry.on("pre_tool_call", cb)
    registry.emit("pre_tool_call")
    assert results == [1]

    assert registry.off("pre_tool_call", cb) is True
    registry.emit("pre_tool_call")
    assert results == [1]  # no new append


def test_remove_nonexistent_callback():
    registry = HookRegistry()
    cb = lambda **kw: None  # noqa: E731
    assert registry.off("pre_tool_call", cb) is False


def test_has_listeners():
    registry = HookRegistry()
    assert registry.has_listeners("pre_tool_call") is False
    registry.on("pre_tool_call", lambda **kw: None)
    assert registry.has_listeners("pre_tool_call") is True


def test_clear_single_event():
    registry = HookRegistry()
    registry.on("pre_tool_call", lambda **kw: None)
    registry.on("post_tool_call", lambda **kw: None)

    registry.clear("pre_tool_call")
    assert registry.has_listeners("pre_tool_call") is False
    assert registry.has_listeners("post_tool_call") is True


def test_clear_all():
    registry = HookRegistry()
    registry.on("pre_tool_call", lambda **kw: None)
    registry.on("post_tool_call", lambda **kw: None)

    registry.clear()
    assert registry.has_listeners("pre_tool_call") is False
    assert registry.has_listeners("post_tool_call") is False


def test_unknown_event_warning():
    registry = HookRegistry()
    # Should not raise, just logs a warning
    registry.on("unknown_event", lambda **kw: None)
    # Callback still registered and fires
    results = registry.emit("unknown_event")
    assert results == [None]


# ── Global hooks instance ───────────────────────────────────────────────────


def test_global_hooks_is_singleton():
    assert isinstance(hooks, HookRegistry)
