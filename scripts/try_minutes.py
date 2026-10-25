import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from minutesai.config import MAX_AUDIO_MB, PROVIDERS
from minutesai.llm import make_client, summarise, transcribe

load_dotenv()  # reads your keys from .env

provider = "OpenAI"
settings = PROVIDERS[provider]
audio_path = Path(sys.argv[1])

size_mb = audio_path.stat().st_size / (1024 * 1024)
if size_mb > MAX_AUDIO_MB:
    sys.exit(f"File is {size_mb:.1f} MB; the limit is {MAX_AUDIO_MB} MB.")

client = make_client(provider, os.environ[settings["env_var"]])

print(f"Transcribing {audio_path.name} ({size_mb:.1f} MB)...")
transcript = transcribe(client, str(audio_path), settings["asr_model"])
print(f"\n--- Transcript (first 500 characters) ---\n{transcript[:500]}\n")

print("Writing minutes...")
minutes = summarise(client, transcript, settings["llm_model"])
print(f"\n--- Minutes ---\n{minutes}")
