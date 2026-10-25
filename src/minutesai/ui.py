# Gradio UI: bring-your-own-key, upload audio or paste a transcript, get minutes.
import logging
import os
import tempfile
from pathlib import Path

import gradio as gr

from minutesai.config import MAX_AUDIO_MB, PROVIDERS
from minutesai.llm import make_client, summarise, transcribe
from minutesai.safety import friendly_error, redact

logger = logging.getLogger(__name__)
PROVIDER = "OpenAI"  # a provider dropdown arrives in M3

PRIVACY_NOTE = """**Privacy:** your key is kept only in this browser session. It's never
saved or logged, and **Remove key** deletes it. Audio is sent to the provider you choose."""


# ---------- key handling ----------


def get_key(keys: dict, provider: str) -> str | None:
    """Session key first; .env key only when ALLOW_ENV_KEYS=true (local dev)."""
    if keys.get(provider):
        return keys[provider]
    if os.getenv("ALLOW_ENV_KEYS", "").lower() == "true":
        return os.getenv(PROVIDERS[provider]["env_var"])
    return None


def save_key(key_text: str, keys: dict):
    """Check the key with a cheap API call, then store it in this session."""
    key_text = key_text.strip()
    if not key_text:
        return keys, "⚠️ Paste a key first.", ""
    try:
        make_client(PROVIDER, key_text).models.list()
    except Exception as error:
        logger.warning("Key check failed: %s", redact(str(error)))
        return keys, f"❌ {friendly_error(error)}", key_text
    new_keys = {**keys, PROVIDER: key_text}  # a new dict; never change the old one
    return new_keys, "✅ Key saved for this browser session.", ""


def remove_key(keys: dict):
    new_keys = {name: key for name, key in keys.items() if name != PROVIDER}
    return new_keys, "🔑 No key set.", ""


# ---------- generating minutes ----------


def save_downloads(minutes: str, transcript: str) -> list[str]:
    folder = Path(tempfile.mkdtemp(prefix="minutesai_"))
    (folder / "minutes.md").write_text(minutes, encoding="utf-8")
    (folder / "transcript.txt").write_text(transcript, encoding="utf-8")
    return [str(folder / "minutes.md"), str(folder / "transcript.txt")]


def generate(keys: dict, audio_path: str | None, pasted_text: str, progress=gr.Progress()):  # noqa: B008
    api_key = get_key(keys, PROVIDER)
    if not api_key:
        raise gr.Error("Add your OpenAI API key first.")
    if not audio_path and not pasted_text.strip():
        raise gr.Error("Upload a recording or paste a transcript.")
    if audio_path and Path(audio_path).stat().st_size > MAX_AUDIO_MB * 1024 * 1024:
        raise gr.Error(f"The recording is over {MAX_AUDIO_MB} MB. Long-audio support comes later.")

    settings = PROVIDERS[PROVIDER]
    try:
        client = make_client(PROVIDER, api_key)
        if pasted_text.strip():
            transcript = pasted_text.strip()
        else:
            progress(0.2, desc="Transcribing audio...")
            transcript = transcribe(client, audio_path, settings["asr_model"])
        progress(0.6, desc="Writing minutes...")
        minutes = summarise(client, transcript, settings["llm_model"])
    except Exception as error:
        logger.warning("Generation failed: %s", redact(str(error)))
        raise gr.Error(friendly_error(error)) from None

    return minutes, transcript, save_downloads(minutes, transcript)


# ---------- layout ----------


def build_ui() -> gr.Blocks:
    start_status = (
        "🧪 Using key from .env (dev mode)" if get_key({}, PROVIDER) else "🔑 No key set."
    )

    with gr.Blocks(title="MinutesAI") as demo:
        keys = gr.State({})  # every browser session gets its own copy

        gr.Markdown("# MinutesAI\nTurn a meeting or lecture recording into structured minutes.")

        with gr.Row():
            with gr.Column(scale=1):
                key_box = gr.Textbox(label="OpenAI API key", type="password", placeholder="sk-...")
                with gr.Row():
                    save_btn = gr.Button("Save key", variant="primary")
                    remove_btn = gr.Button("Remove key")
                key_status = gr.Markdown(start_status)
                gr.Markdown(PRIVACY_NOTE)

            with gr.Column(scale=2):
                audio = gr.Audio(
                    sources=["upload"],
                    type="filepath",
                    label=f"Recording (up to {MAX_AUDIO_MB} MB)",
                )
                pasted = gr.Textbox(label="...or paste a transcript instead", lines=5)
                generate_btn = gr.Button("Generate minutes", variant="primary")

        minutes_box = gr.Markdown()
        with gr.Accordion("Transcript", open=False):
            transcript_box = gr.Textbox(lines=10, show_label=False)
        downloads = gr.File(label="Downloads", file_count="multiple")

        save_btn.click(save_key, [key_box, keys], [keys, key_status, key_box])
        remove_btn.click(remove_key, [keys], [keys, key_status, key_box])
        generate_btn.click(
            generate, [keys, audio, pasted], [minutes_box, transcript_box, downloads]
        )

    return demo
