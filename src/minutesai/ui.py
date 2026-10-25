import logging
import os
import tempfile
from pathlib import Path

import gradio as gr

from minutesai.config import PROVIDERS
from minutesai.llm import create_minutes, make_client
from minutesai.safety import friendly_error, redact
from minutesai.schema import to_markdown

logger = logging.getLogger(__name__)
DEFAULT_PROVIDER = "OpenAI"

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


def key_status(keys: dict, provider: str) -> str:
    if keys.get(provider):
        return f"✅ {provider} key saved for this browser session."
    if get_key(keys, provider):
        return f"🧪 Using {provider} key from .env (dev mode)."
    return f"🔑 No {provider} key set."


def key_link(provider: str) -> str:
    return f"Get a key: [{provider} key page]({PROVIDERS[provider]['key_url']})"


def save_key(provider: str, key_text: str, keys: dict):
    """Check the key with a cheap API call, then store it in this session."""
    key_text = key_text.strip()
    if not key_text:
        return keys, "⚠️ Paste a key first.", ""
    try:
        make_client(provider, key_text).models.list()
    except Exception as error:
        logger.warning("Key check failed: %s", redact(str(error)))
        return keys, f"❌ {friendly_error(error)}", key_text
    new_keys = {**keys, provider: key_text}  # a new dict; never change the old one
    return new_keys, key_status(new_keys, provider), ""


def remove_key(provider: str, keys: dict):
    new_keys = {name: key for name, key in keys.items() if name != provider}
    return new_keys, key_status(new_keys, provider), ""


def change_provider(provider: str, keys: dict):
    """Update the key box, status and link when the dropdown changes."""
    key_box = gr.Textbox(label=f"{provider} API key", value="")
    return key_box, key_status(keys, provider), key_link(provider)


# ---------- generating minutes ----------


def save_downloads(minutes: str, transcript: str) -> list[str]:
    folder = Path(tempfile.mkdtemp(prefix="minutesai_"))
    (folder / "minutes.md").write_text(minutes, encoding="utf-8")
    (folder / "transcript.txt").write_text(transcript, encoding="utf-8")
    return [str(folder / "minutes.md"), str(folder / "transcript.txt")]


def generate(
    provider: str,
    keys: dict,
    audio_path: str | None,
    pasted_text: str,
    progress=gr.Progress(),  # noqa: B008
):
    api_key = get_key(keys, provider)
    if not api_key:
        raise gr.Error(f"Add your {provider} API key first.")
    if not audio_path and not pasted_text.strip():
        raise gr.Error("Upload a recording or paste a transcript.")

    progress(0.1, desc="Working... long recordings take a few minutes.")
    try:
        minutes, transcript = create_minutes(
            provider, api_key, audio_path=audio_path, transcript=pasted_text
        )
    except Exception as error:
        logger.warning("Generation failed: %s", redact(str(error)))
        raise gr.Error(friendly_error(error)) from None

    markdown = to_markdown(minutes)
    return markdown, transcript, save_downloads(markdown, transcript)


# ---------- layout ----------


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="MinutesAI") as demo:
        keys = gr.State({})  # every browser session gets its own copy

        gr.Markdown("# MinutesAI\nTurn a meeting or lecture recording into structured minutes.")

        with gr.Row():
            with gr.Column(scale=1):
                provider = gr.Dropdown(
                    choices=list(PROVIDERS), value=DEFAULT_PROVIDER, label="Provider"
                )
                link = gr.Markdown(key_link(DEFAULT_PROVIDER))
                key_box = gr.Textbox(label=f"{DEFAULT_PROVIDER} API key", type="password")
                with gr.Row():
                    save_btn = gr.Button("Save key", variant="primary")
                    remove_btn = gr.Button("Remove key")
                status = gr.Markdown(key_status({}, DEFAULT_PROVIDER))
                gr.Markdown(PRIVACY_NOTE)

            with gr.Column(scale=2):
                audio = gr.Audio(
                    sources=["upload"],
                    type="filepath",
                    label="Recording",
                )
                pasted = gr.Textbox(label="...or paste a transcript instead", lines=5)
                generate_btn = gr.Button("Generate minutes", variant="primary")

        minutes_box = gr.Markdown()
        with gr.Accordion("Transcript", open=False):
            transcript_box = gr.Textbox(lines=10, show_label=False)
        downloads = gr.File(label="Downloads", file_count="multiple")

        provider.change(change_provider, [provider, keys], [key_box, status, link])
        save_btn.click(save_key, [provider, key_box, keys], [keys, status, key_box])
        remove_btn.click(remove_key, [provider, keys], [keys, status, key_box])
        generate_btn.click(
            generate, [provider, keys, audio, pasted], [minutes_box, transcript_box, downloads]
        )

    return demo
