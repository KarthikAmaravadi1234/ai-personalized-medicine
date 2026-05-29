from backend.llm import OpenAICircuit, is_quota_or_auth_error


def test_circuit_starts_available():
    c = OpenAICircuit(cooldown_seconds=60)
    assert c.is_available() is True
    assert c.status()["available"] is True


def test_circuit_trips_and_blocks():
    c = OpenAICircuit(cooldown_seconds=60)
    c.trip("insufficient_quota")
    assert c.is_available() is False
    status = c.status()
    assert status["available"] is False
    assert status["cooldown_remaining_s"] > 0
    assert status["last_reason"] == "insufficient_quota"


def test_circuit_recovers_after_cooldown():
    c = OpenAICircuit(cooldown_seconds=0)  # immediate recovery
    c.trip("rate limited")
    assert c.is_available() is True


def test_circuit_reset():
    c = OpenAICircuit(cooldown_seconds=60)
    c.trip("boom")
    c.reset()
    assert c.is_available() is True


def test_quota_detection_ignores_generic_errors():
    assert is_quota_or_auth_error(ValueError("not an openai error")) is False
