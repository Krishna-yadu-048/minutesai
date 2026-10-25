"""MinutesAI entry point: the API and the Gradio UI on one server.

Run with: uv run app.py
- UI:       http://127.0.0.1:7860
- API docs: http://127.0.0.1:7860/docs
"""

import gradio as gr
import uvicorn
from dotenv import load_dotenv

from minutesai.api import api
from minutesai.ui import build_ui

load_dotenv()  # load .env before the UI checks for a dev key
app = gr.mount_gradio_app(api, build_ui(), path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860)
