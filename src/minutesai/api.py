"""REST API: POST /minutes with audio or a transcript; the key goes in a header."""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

import openai
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from minutesai.config import PROVIDERS
from minutesai.llm import create_minutes
from minutesai.safety import friendly_error, redact
from minutesai.schema import Minutes, to_markdown

logger = logging.getLogger(__name__)
api = FastAPI(title="MinutesAI API", description="Turn recordings into structured minutes.")


class MinutesResponse(BaseModel):
    minutes: Minutes
    markdown: str
    transcript: str


@api.get("/health")
def health() -> dict:
    return {"status": "ok"}


@api.post("/minutes", response_model=MinutesResponse)
def make_minutes(
    x_api_key: Annotated[str | None, Header()] = None,
    provider: Annotated[str, Form()] = "OpenAI",
    transcript: Annotated[str, Form()] = "",
    audio: Annotated[UploadFile | None, File()] = None,
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Send your API key in the X-API-Key header.")
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider must be one of {list(PROVIDERS)}.")
    if audio is None and not transcript.strip():
        raise HTTPException(status_code=400, detail="Send an audio file or a transcript.")

    try:
        if audio is not None:
            # Save the upload to a temporary folder that's deleted afterwards.
            with tempfile.TemporaryDirectory() as folder:
                audio_path = Path(folder) / Path(audio.filename or "audio.mp3").name
                with open(audio_path, "wb") as saved:
                    shutil.copyfileobj(audio.file, saved)
                minutes, text = create_minutes(provider, x_api_key, audio_path=str(audio_path))
        else:
            minutes, text = create_minutes(provider, x_api_key, transcript=transcript)
    except Exception as error:
        logger.warning("API request failed: %s", redact(str(error)))
        status = 401 if isinstance(error, openai.AuthenticationError) else 502
        raise HTTPException(status_code=status, detail=friendly_error(error)) from None

    return MinutesResponse(minutes=minutes, markdown=to_markdown(minutes), transcript=text)
