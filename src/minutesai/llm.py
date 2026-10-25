import tempfile

from openai import OpenAI
from pydantic import ValidationError

from minutesai.audio import needs_splitting, split_audio
from minutesai.config import PROVIDERS
from minutesai.schema import Minutes

SYSTEM_PROMPT = """You produce minutes of meetings from transcripts.
Use only facts stated in the transcript; never invent names, dates or owners.
If something isn't stated, use null or an empty list.

Reply with a JSON object only, in exactly this shape:
{
  "title": "short descriptive title",
  "date": "date if stated, else null",
  "attendees": ["names of people present or speaking"],
  "summary": "3-6 sentence summary",
  "discussion_points": ["..."],
  "decisions": ["decisions or motions passed"],
  "action_items": [{"task": "...", "owner": "name or null", "due": "date or null"}]
}"""


def make_client(provider: str, api_key: str) -> OpenAI:

    settings = PROVIDERS[provider]
    return OpenAI(api_key=api_key, base_url=settings["base_url"])


def transcribe(client: OpenAI, audio_path: str, model: str) -> str:
    with open(audio_path, "rb") as audio_file:
        return client.audio.transcriptions.create(
            model=model, file=audio_file, response_format="text"
        )


def transcribe_file(client: OpenAI, audio_path: str, model: str) -> str:
    """Transcribe any length of recording, splitting it first if it's too big."""
    if not needs_splitting(audio_path):
        return transcribe(client, audio_path, model)
    with tempfile.TemporaryDirectory() as folder:  # deleted automatically afterwards
        chunks = split_audio(audio_path, folder)
        return " ".join(transcribe(client, chunk, model) for chunk in chunks)


def ask_for_json(client: OpenAI, messages: list[dict], model: str) -> str:
    """Send the conversation in JSON mode and return the reply text."""
    response = client.chat.completions.create(
        model=model, messages=messages, response_format={"type": "json_object"}
    )
    return response.choices[0].message.content


def summarise(client: OpenAI, transcript: str, model: str) -> Minutes:
    """Turn a transcript into validated Minutes, retrying once if the JSON is bad."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Write minutes for this transcript:\n\n{transcript}"},
    ]
    reply = ask_for_json(client, messages, model)
    try:
        return Minutes.model_validate_json(reply)
    except ValidationError as error:
        # One retry: show the model its reply and what was wrong with it.
        messages += [
            {"role": "assistant", "content": reply},
            {
                "role": "user",
                "content": f"That JSON was invalid:\n{error}\nReply with corrected JSON only.",
            },
        ]
        reply = ask_for_json(client, messages, model)
        return Minutes.model_validate_json(reply)  # if this fails too, the UI shows an error


def create_minutes(
    provider: str, api_key: str, audio_path: str | None = None, transcript: str = ""
) -> tuple[Minutes, str]:
    """The full pipeline: transcribe if needed, then summarise. Used by the UI and the API."""
    settings = PROVIDERS[provider]
    client = make_client(provider, api_key)
    if not transcript.strip():
        transcript = transcribe_file(client, audio_path, settings["asr_model"])
    minutes = summarise(client, transcript.strip(), settings["llm_model"])
    return minutes, transcript.strip()
