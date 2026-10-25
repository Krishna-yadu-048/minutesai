from pathlib import Path

from pydub import AudioSegment

from minutesai.audio import split_audio


def test_long_audio_is_split_into_small_chunks(tmp_path):
    recording = tmp_path / "long.wav"
    AudioSegment.silent(duration=3 * 60 * 1000).export(recording, format="wav")  # 3 minutes

    chunks = split_audio(str(recording), str(tmp_path), chunk_minutes=1)

    assert len(chunks) == 3
    for chunk in chunks:
        assert Path(chunk).exists()
        assert Path(chunk).stat().st_size < 25 * 1024 * 1024