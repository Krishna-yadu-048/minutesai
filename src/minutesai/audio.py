"""Split recordings that are too big for the provider into smaller MP3 files."""

from pathlib import Path

from pydub import AudioSegment

from minutesai.config import MAX_AUDIO_MB

CHUNK_MINUTES = 10


def needs_splitting(audio_path: str) -> bool:
    return Path(audio_path).stat().st_size > MAX_AUDIO_MB * 1024 * 1024


def split_audio(audio_path: str, folder: str, chunk_minutes: int = CHUNK_MINUTES) -> list[str]:
    """Cut the recording into chunks and save them as small MP3s in `folder`."""
    audio = AudioSegment.from_file(audio_path).set_channels(1)  # mono halves the size
    chunk_ms = chunk_minutes * 60 * 1000

    chunk_paths = []
    for number, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start : start + chunk_ms]  # pydub slices by milliseconds
        path = Path(folder) / f"chunk_{number:03d}.mp3"
        chunk.export(path, format="mp3", bitrate="64k")
        chunk_paths.append(str(path))
    return chunk_paths
