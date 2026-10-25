"""Provider settings and app limits."""

PROVIDERS = {
    "OpenAI": {
        "base_url": None,  # None means the official OpenAI endpoint
        "asr_model": "gpt-4o-mini-transcribe",
        "llm_model": "gpt-4.1-mini",
        "env_var": "OPENAI_API_KEY",
    },
    "Groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "asr_model": "whisper-large-v3-turbo",
        "llm_model": "llama-3.3-70b-versatile",
        "env_var": "GROQ_API_KEY",
    },
}

MAX_AUDIO_MB = 25  # OpenAI and Groq both reject audio files larger than this
