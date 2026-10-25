import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from minutesai.llm import make_client, summarise
from minutesai.schema import ActionItem, Minutes, to_markdown

GOOD_JSON = json.dumps(
    {
        "title": "Weekly sync",
        "attendees": ["Asha", "Ravi"],
        "summary": "The team reviewed progress.",
        "action_items": [{"task": "Send notes", "owner": "Asha"}],
    }
)


def fake_client(*replies: str) -> MagicMock:
    """A stand-in API client that returns the given replies in order."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=text))]) for text in replies
    ]
    return client


def test_groq_client_uses_groq_url():
    client = make_client("Groq", "gsk_test12345678")
    assert str(client.base_url).startswith("https://api.groq.com/openai/v1")


def test_good_json_needs_one_call():
    client = fake_client(GOOD_JSON)
    minutes = summarise(client, "transcript", "any-model")
    assert minutes.title == "Weekly sync"
    assert client.chat.completions.create.call_count == 1


def test_bad_json_is_retried_once():
    client = fake_client("this is not json", GOOD_JSON)
    minutes = summarise(client, "transcript", "any-model")
    assert minutes.title == "Weekly sync"
    assert client.chat.completions.create.call_count == 2


def test_two_bad_replies_raise_validation_error():
    client = fake_client("not json", "still not json")
    with pytest.raises(ValidationError):
        summarise(client, "transcript", "any-model")


def test_markdown_handles_missing_values():
    minutes = Minutes(title="Sync", summary="Short.", action_items=[ActionItem(task="Fix bug")])
    markdown = to_markdown(minutes)
    assert markdown.startswith("# Sync")
    assert "_None recorded._" in markdown  # no decisions were given
    assert "owner: unassigned" in markdown
