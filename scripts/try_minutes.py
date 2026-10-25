"""Quick end-to-end check: audio file -> transcript -> minutes.

Usage: uv run scripts/try_minutes.py samples/denver_extract.mp3 [OpenAI|Groq]
"""

import os
import sys

from dotenv import load_dotenv

from minutesai.config import PROVIDERS
from minutesai.llm import create_minutes
from minutesai.schema import to_markdown

load_dotenv()  # reads your keys from .env

audio_path = sys.argv[1]
provider = sys.argv[2] if len(sys.argv) > 2 else "OpenAI"
api_key = os.environ[PROVIDERS[provider]["env_var"]]

print(f"Creating minutes for {audio_path} with {provider}...")
minutes, transcript = create_minutes(provider, api_key, audio_path=audio_path)
print(f"\n--- Transcript (first 500 characters) ---\n{transcript[:500]}\n")
print(f"--- Minutes ---\n{to_markdown(minutes)}")
