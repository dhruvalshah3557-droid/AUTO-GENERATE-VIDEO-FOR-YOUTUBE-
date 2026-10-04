from pathlib import Path

import librosa
import numpy as np

HOP_LENGTH = 512
N_FFT = 2048


def track_beats(audio_path: Path) -> dict:
    y, sr = librosa.load(str(audio_path), sr=22050)
    percussive = librosa.effects.percussive(y)
    onset_env = librosa.onset.onset_strength(
        y=percussive,
        sr=sr,
        hop_length=HOP_LENGTH,
        n_fft=N_FFT,
        aggregate=np.median,
    )
    tempo, frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=HOP_LENGTH,
    )
    if isinstance(tempo, np.ndarray):
        tempo = float(tempo.squeeze())
    times = librosa.frames_to_time(frames, sr=sr, hop_length=HOP_LENGTH)
    duration = float(librosa.get_duration(y=y, sr=sr))
    if len(times) == 0:
        step = 60.0 / 80.0
        times = np.arange(0.0, duration, step)
        tempo = 80.0
    return {
        "tempo": float(tempo),
        "times": [float(t) for t in times],
        "duration": duration,
        "sample_rate": int(sr),
    }


def save_beats_csv(times: list[float], csv_path: Path) -> Path:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(str(csv_path), np.array(times, dtype=np.float64), delimiter=",")
    return csv_path
