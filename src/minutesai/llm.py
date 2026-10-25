from openai import OpenAI

from minutesai.config import PROVIDERS

SYSTEM_PROMPT = """You produce minutes of meetings from transcripts.
Use only facts stated in the transcript; never invent names, dates or owners.
Write in markdown with these sections: Summary (with attendees, location and date
if stated), Discussion points, Takeaways, and Action items with owners."""


def make_client(provider: str, api_key: str) -> OpenAI:

    settings = PROVIDERS[provider]
    return OpenAI(api_key=api_key, base_url=settings["base_url"])


def transcribe(client: OpenAI, audio_path: str, model: str) -> str:
    with open(audio_path, "rb") as audio_file:
        return client.audio.transcriptions.create(
            model=model, file=audio_file, response_format="text"
        )


def summarise(client: OpenAI, transcript: str, model: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Write minutes for this transcript:\n\n{transcript}"},
    ]
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content
