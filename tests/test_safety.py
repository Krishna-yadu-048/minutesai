from minutesai.safety import friendly_error, redact


def test_redact_hides_openai_and_groq_keys():
    text = "keys: sk-proj-abc123def456ghi and gsk_abc123def456ghi"
    result = redact(text)
    assert "abc123" not in result
    assert result.count("[REDACTED]") == 2


def test_redact_leaves_normal_text_alone():
    text = "The task-list was discussed in the meeting."
    assert redact(text) == text


def test_unknown_errors_get_a_generic_message():
    message = friendly_error(ValueError("secret details sk-abc123def456"))
    assert message == "Something went wrong (ValueError). Please try again."
