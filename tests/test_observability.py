from unittest.mock import MagicMock

import pytest

from nova.config import DEFAULT_CONFIG, ConfigError, _validate_config
from nova.observability import (
    NoOpObservability,
    create_observability,
    redact,
    redact_text,
    should_sample,
)


def test_observability_defaults_disabled():
    observer = create_observability(DEFAULT_CONFIG)
    assert isinstance(observer, NoOpObservability)


def test_sample_rate_is_validated():
    config = {**DEFAULT_CONFIG, "observability": {"sample_rate": 1.1}}
    with pytest.raises(ConfigError, match="sample_rate"):
        _validate_config(config)


def test_sampling_boundaries_are_deterministic():
    assert should_sample(0.0, random_value=0.0) is False
    assert should_sample(1.0, random_value=0.999) is True


def test_redact_removes_secret_shaped_values():
    value = {"api_key": "secret", "authorization": "Bearer token", "nested": "ok"}
    result = redact(value)
    assert result["api_key"] == "[REDACTED]"
    assert result["authorization"] == "[REDACTED]"
    assert result["nested"] == "ok"


def test_redact_handles_common_secret_key_variants_and_bearer_values():
    value = {
        "apiKey": "one",
        "api-key": "two",
        "client_secret": "three",
        "private_key": "four",
        "cookie": "five",
        "authorization": "six",
        "header": "Bearer abc.def.ghi",
        "ordinary": "Bearer is an ordinary word here",
    }

    result = redact(value)

    for key in ("apiKey", "api-key", "client_secret", "private_key", "cookie", "authorization"):
        assert result[key] == "[REDACTED]"
    assert result["header"] == "Bearer [REDACTED]"
    assert result["ordinary"] == "Bearer is an ordinary word here"


def test_redact_handles_normalized_secret_names_and_headers():
    value = {
        "api_token": "one",
        "auth_token": "two",
        "x-api-key": "three",
        "access_key": "four",
        "set-cookie": "five",
        "credential": "six",
        "X-Auth-Token": "seven",
        "safe": "ok",
    }

    result = redact(value)

    for key in value:
        if key != "safe":
            assert result[key] == "[REDACTED]"
    assert result["safe"] == "ok"


def test_redact_masks_secret_patterns_embedded_in_text():
    text = (
        "api_key=secret-one password: pass-two client_secret = 'secret three' "
        "Authorization: Bearer bearer-token ordinary text"
    )

    result = redact(text)

    assert "secret-one" not in result
    assert "pass-two" not in result
    assert "secret three" not in result
    assert "bearer-token" not in result
    assert "ordinary text" in result
    assert "api_key=[REDACTED]" in result
    assert "Authorization: Bearer [REDACTED]" in result


def test_redact_preserves_ordinary_bearer_text():
    assert redact("Bearer is an ordinary word here") == "Bearer is an ordinary word here"


def test_redact_masks_generic_credential_assignments_in_text():
    result = redact_text("token=secret auth: 'auth-secret' access = access-secret")

    assert result == "token=[REDACTED] auth: '[REDACTED]' access = [REDACTED]"


def test_redact_preserves_ordinary_token_auth_and_access_text():
    text = "token budget, authenticate the access request, and access to the file"

    assert redact_text(text) == text


def test_adapter_emits_run_llm_tool_policy_and_verification_observations():
    client = MagicMock()
    root = MagicMock()
    client.start_as_current_observation.return_value = root
    config = {
        **DEFAULT_CONFIG,
        "observability": {
            "enabled": True,
            "provider": "langfuse",
            "sample_rate": 1.0,
            "capture_input": False,
            "capture_output": False,
            "langfuse": {"public_key": "pk", "secret_key": "sk"},
        },
    }
    observer = create_observability(config, client_factory=lambda _: client)
    with observer.run("run-1", "hello"):
        observer.llm("model", input_data="prompt", output_data="answer")
        observer.tool("read_file", input_data={"path": "/tmp/x"}, output_data="ok")
        observer.policy("read_file", allowed=True)
        observer.verification("read_file", status="verified")
    names = [call.kwargs["name"] for call in client.start_as_current_observation.call_args_list]
    assert names == ["nova.run", "nova.llm", "nova.tool", "nova.policy", "nova.verification"]
    assert "prompt" not in str(client.start_as_current_observation.call_args_list)
    observer.shutdown()
    client.flush.assert_called_once()


def test_missing_sdk_is_noop_and_flush_never_raises():
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: (_ for _ in ()).throw(ImportError("missing")),
    )
    with observer.run("id", "goal"):
        observer.tool("x", output_data="y")
    observer.shutdown()
    assert isinstance(observer, NoOpObservability)


def test_telemetry_error_does_not_escape_context():
    client = MagicMock()
    client.start_as_current_observation.side_effect = RuntimeError("telemetry down")
    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {"enabled": True, "provider": "langfuse", "sample_rate": 1.0},
        },
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal"):
        pass
    observer.shutdown()


def test_shutdown_can_be_disabled():
    client = MagicMock()
    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {"enabled": True, "provider": "langfuse", "flush_at_shutdown": False},
        },
        client_factory=lambda _: client,
    )
    observer.shutdown()
    client.flush.assert_not_called()


def test_capture_opt_in_passes_payload():
    client = MagicMock()
    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {
                "enabled": True,
                "provider": "langfuse",
                "capture_input": True,
                "capture_output": True,
            },
        },
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal"):
        observer.llm("model", input_data="prompt", output_data="answer")
    call = client.start_as_current_observation.call_args_list[1]
    assert call.kwargs["input"] == "prompt"
    assert call.kwargs["output"] == "answer"


def test_observation_context_handles_sdk_context_manager():
    client = MagicMock()
    observation = MagicMock()
    observation.__enter__.return_value = observation
    observation.__exit__.return_value = False
    client.start_as_current_observation.return_value = observation
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal"):
        pass
    observation.update.assert_called()
    observation.end.assert_called()


def test_noop_methods_are_safe():
    observer = NoOpObservability()
    with observer.run("id", "goal"):
        observer.llm("m")
        observer.tool("t")
        observer.policy("t", allowed=False)
        observer.verification("t", status="failed")
    observer.shutdown()
    assert observer.enabled is False


def test_nested_values_are_bounded():
    assert len(redact("x" * 2000)) <= 1000
    assert redact({"password": "x"})["password"] == "[REDACTED]"


def test_config_defaults_include_observability():
    assert DEFAULT_CONFIG["observability"]["enabled"] is False
    assert DEFAULT_CONFIG["observability"]["langfuse"]["base_url"] == "https://cloud.langfuse.com"
    assert DEFAULT_CONFIG["observability"]["capture_input"] is False
    assert DEFAULT_CONFIG["observability"]["capture_output"] is False


def test_client_factory_receives_config():
    client = MagicMock()
    received = []
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda cfg: received.append(cfg) or client,
    )
    assert observer.enabled and received
    assert received[0]["base_url"] == "https://cloud.langfuse.com"


def test_unresolved_langfuse_placeholders_do_not_initialize_client(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    factory = MagicMock()
    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {
                "enabled": True,
                "provider": "langfuse",
                "langfuse": {"public_key": "${MISSING_PK}", "secret_key": "${MISSING_SK}"},
            },
        },
        client_factory=factory,
    )
    assert isinstance(observer, NoOpObservability)
    factory.assert_not_called()


def test_langfuse_placeholders_resolve_from_environment(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "env-pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "env-sk")
    factory = MagicMock()

    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {
                "enabled": True,
                "provider": "langfuse",
                "langfuse": {
                    "public_key": "${LANGFUSE_PUBLIC_KEY}",
                    "secret_key": "${LANGFUSE_SECRET_KEY}",
                },
            },
        },
        client_factory=factory,
    )

    assert observer.enabled
    assert factory.call_args.args[0]["public_key"] == "env-pk"
    assert factory.call_args.args[0]["secret_key"] == "env-sk"


def test_provider_other_than_langfuse_is_noop():
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "other"}}
    )
    assert isinstance(observer, NoOpObservability)


def test_flush_error_is_swallowed():
    client = MagicMock()
    client.flush.side_effect = RuntimeError("down")
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    observer.shutdown()


def test_secret_redaction_in_nested_collections():
    result = redact([{"token": "secret"}, "safe"])
    assert result == [{"token": "[REDACTED]"}, "safe"]


def test_run_context_does_not_require_capture():
    client = MagicMock()
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with observer.run("id", "secret goal"):
        pass
    kwargs = client.start_as_current_observation.call_args.kwargs
    assert "input" not in kwargs


def test_sample_rate_invalid_type():
    with pytest.raises(ConfigError, match="sample_rate"):
        _validate_config({**DEFAULT_CONFIG, "observability": {"sample_rate": "bad"}})


def test_sample_rate_negative():
    with pytest.raises(ConfigError, match="sample_rate"):
        _validate_config({**DEFAULT_CONFIG, "observability": {"sample_rate": -0.1}})


def test_client_initialization_errors_are_safe():
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: 1 / 0,
    )
    assert isinstance(observer, NoOpObservability)


def test_flush_called_once_on_explicit_shutdown():
    client = MagicMock()
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    observer.shutdown()
    observer.shutdown()
    assert client.flush.call_count == 1


def test_observer_has_session_and_metadata():
    client = MagicMock()
    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {
                "enabled": True,
                "provider": "langfuse",
                "environment": "test",
                "release": "r1",
            },
        },
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal", session_id="session"):
        pass
    kwargs = client.start_as_current_observation.call_args.kwargs
    assert kwargs["metadata"]["session_id"] == "session"
    assert kwargs["metadata"]["environment"] == "test"


def test_update_failure_is_safe():
    client = MagicMock()
    client.start_as_current_observation.return_value.update.side_effect = RuntimeError("down")
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal"):
        pass


def test_agent_exception_is_not_swallowed_by_telemetry():
    client = MagicMock()
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with pytest.raises(ValueError, match="agent"), observer.run("id", "goal"):
        raise ValueError("agent")


def test_root_observation_is_named_run():
    client = MagicMock()
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal"):
        pass
    assert client.start_as_current_observation.call_args_list[0].kwargs["as_type"] == "span"


def test_verification_does_not_capture_result_when_output_capture_is_disabled():
    client = MagicMock()
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with observer.run("id", "goal"):
        observer.verification("tool", status="failed", result="secret tool output")
    assert "secret tool output" not in str(client.start_as_current_observation.call_args_list)


def test_sampling_is_decided_for_each_run(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("nova.observability.random.random", lambda: 0.5)
    observer = create_observability(
        {
            **DEFAULT_CONFIG,
            "observability": {"enabled": True, "provider": "langfuse", "sample_rate": 0.75},
        },
        client_factory=lambda _: client,
    )
    with observer.run("one", "goal"):
        pass
    with observer.run("two", "goal"):
        pass
    assert client.start_as_current_observation.call_count == 2


def test_real_context_manager_uses_entered_object_and_exception_tuple():
    class Entered:
        def __init__(self):
            self.updated = False
            self.ended = False

        def update(self, **kwargs):
            self.updated = True

        def end(self):
            self.ended = True

    class Observation:
        def __init__(self):
            self.entered = Entered()
            self.exit_args = None

        def __enter__(self):
            return self.entered

        def __exit__(self, *args):
            self.exit_args = args

    class Client:
        def __init__(self):
            self.observation = Observation()

        def start_as_current_observation(self, **kwargs):
            return self.observation

    client = Client()
    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: client,
    )
    with pytest.raises(RuntimeError), observer.run("id", "goal"):
        raise RuntimeError("boom")
    assert client.observation.entered.updated
    assert client.observation.entered.ended
    assert client.observation.exit_args is not None
    assert client.observation.exit_args[0] is RuntimeError


def test_sdk_context_exit_failure_is_swallowed_but_agent_failure_propagates():
    class FailingObservation:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            raise RuntimeError("sdk export failed")

        def update(self, **kwargs):
            pass

    class Client:
        def start_as_current_observation(self, **kwargs):
            return FailingObservation()

    observer = create_observability(
        {**DEFAULT_CONFIG, "observability": {"enabled": True, "provider": "langfuse"}},
        client_factory=lambda _: Client(),
    )
    with observer.run("id", "goal"):
        pass
    with pytest.raises(ValueError, match="agent"), observer.run("id", "goal"):
        raise ValueError("agent")
