from unittest.mock import MagicMock

from minutesai import ui


def fake_client_factory(works: bool):
    """Return a stand-in for make_client whose key check passes or fails."""
    client = MagicMock()
    if not works:
        client.models.list.side_effect = RuntimeError("bad key sk-secret12345678")
    return lambda provider, key: client


def test_two_sessions_keep_separate_keys(monkeypatch):
    monkeypatch.setattr(ui, "make_client", fake_client_factory(works=True))
    session_a, _, _ = ui.save_key("OpenAI", "sk-aaaaaaaaaaaa", {})
    session_b, _, _ = ui.save_key("OpenAI", "sk-bbbbbbbbbbbb", {})
    assert session_a == {"OpenAI": "sk-aaaaaaaaaaaa"}
    assert session_b == {"OpenAI": "sk-bbbbbbbbbbbb"}


def test_valid_key_is_saved_and_box_cleared(monkeypatch):
    monkeypatch.setattr(ui, "make_client", fake_client_factory(works=True))
    keys, status, box = ui.save_key("OpenAI", "  sk-good12345678  ", {})
    assert keys == {"OpenAI": "sk-good12345678"}  # spaces trimmed
    assert status.startswith("✅")
    assert box == ""


def test_invalid_key_is_not_saved_or_shown(monkeypatch):
    monkeypatch.setattr(ui, "make_client", fake_client_factory(works=False))
    keys, status, _ = ui.save_key("OpenAI", "sk-secret12345678", {})
    assert keys == {}
    assert "secret" not in status


def test_remove_key_clears_it():
    keys, status, box = ui.remove_key("OpenAI", {"OpenAI": "sk-good12345678"})
    assert keys == {}
    assert "No OpenAI key" in status


def test_each_provider_has_its_own_slot(monkeypatch):
    monkeypatch.setattr(ui, "make_client", fake_client_factory(works=True))
    keys, _, _ = ui.save_key("OpenAI", "sk-openai12345678", {})
    keys, _, _ = ui.save_key("Groq", "gsk_groq12345678", keys)
    assert keys == {"OpenAI": "sk-openai12345678", "Groq": "gsk_groq12345678"}
    keys, _, _ = ui.remove_key("Groq", keys)
    assert keys == {"OpenAI": "sk-openai12345678"}


def test_env_key_only_used_when_allowed(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fromenv12345678")
    monkeypatch.setenv("ALLOW_ENV_KEYS", "false")
    assert ui.get_key({}, "OpenAI") is None
    monkeypatch.setenv("ALLOW_ENV_KEYS", "true")
    assert ui.get_key({}, "OpenAI") == "sk-fromenv12345678"
