import math
from pathlib import Path

import numpy as np
import soundfile as sf

from generator.brand import ASSETS, TEMPO_BPM, BEATS_PER_BAR, BARS


SAMPLE_RATE = 44100


def _envelope(n, attack=0.02, release=0.25, sr=SAMPLE_RATE):
    env = np.ones(n, dtype=np.float64)
    a = min(n, int(attack * sr))
    r = min(n, int(release * sr))
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a)
    if r > 0:
        env[-r:] *= np.linspace(1.0, 0.0, r)
    return env


def _tone(freq, duration, volume=0.12, wave="sine"):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    if wave == "triangle":
        sig = 2.0 * np.abs(2.0 * (t * freq - np.floor(t * freq + 0.5))) - 1.0
        sig *= 0.7
    else:
        sig = np.sin(2.0 * math.pi * freq * t)
        sig += 0.18 * np.sin(4.0 * math.pi * freq * t)
        sig += 0.06 * np.sin(6.0 * math.pi * freq * t)
    sig *= _envelope(n, attack=0.03, release=max(0.18, duration * 0.45))
    return sig * volume


def _pad(freqs, duration, volume=0.045):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    sig = np.zeros(n, dtype=np.float64)
    for i, f in enumerate(freqs):
        detune = 1.0 + (0.003 if i % 2 == 0 else -0.003)
        sig += np.sin(2.0 * math.pi * f * detune * t)
    sig /= max(1, len(freqs))
    sig *= _envelope(n, attack=0.6, release=1.4)
    return sig * volume


def _soft_click(duration=0.08, volume=0.035):
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) / SAMPLE_RATE
    noise = np.random.default_rng(7).normal(0, 1, n) * np.exp(-t * 55)
    tick = np.sin(2.0 * math.pi * 1800 * t) * np.exp(-t * 40)
    return (noise * 0.25 + tick) * volume


def generate_brand_score(out_path: Path | None = None, bars: int = BARS) -> Path:
    beat = 60.0 / TEMPO_BPM
    duration = bars * BEATS_PER_BAR * beat
    n = int(duration * SAMPLE_RATE) + SAMPLE_RATE
    mix = np.zeros(n, dtype=np.float64)

    chords = [
        [130.81, 164.81, 196.00, 261.63],
        [146.83, 174.61, 220.00, 293.66],
        [110.00, 164.81, 196.00, 246.94],
        [98.00, 146.83, 196.00, 246.94],
    ]
    melody = [
        392.00, 440.00, 523.25, 493.88,
        440.00, 392.00, 349.23, 392.00,
        523.25, 587.33, 659.25, 587.33,
        523.25, 440.00, 493.88, 523.25,
        392.00, 349.23, 392.00, 440.00,
        523.25, 493.88, 440.00, 392.00,
        329.63, 349.23, 392.00, 440.00,
        523.25, 493.88, 440.00, 392.00,
    ]

    rng = np.random.default_rng(1984)
    for bar in range(bars):
        start = int(bar * BEATS_PER_BAR * beat * SAMPLE_RATE)
        chord = chords[bar % len(chords)]
        pad = _pad(chord, BEATS_PER_BAR * beat + 0.4, volume=0.05)
        end = min(n, start + len(pad))
        mix[start:end] += pad[: end - start]
        for b in range(BEATS_PER_BAR):
            beat_start = int((bar * BEATS_PER_BAR + b) * beat * SAMPLE_RATE)
            note = melody[(bar * BEATS_PER_BAR + b) % len(melody)]
            tone = _tone(note, beat * 0.92, volume=0.11, wave="sine")
            end_t = min(n, beat_start + len(tone))
            mix[beat_start:end_t] += tone[: end_t - beat_start]
            if b in (0, 2):
                bass = _tone(chord[0] / 2.0, beat * 1.4, volume=0.09, wave="triangle")
                end_b = min(n, beat_start + len(bass))
                mix[beat_start:end_b] += bass[: end_b - beat_start]
            click = _soft_click()
            end_c = min(n, beat_start + len(click))
            mix[beat_start:end_c] += click[: end_c - beat_start]

    sparkle_times = np.linspace(0.4, duration - 0.5, bars * 2)
    for t0 in sparkle_times:
        idx = int(t0 * SAMPLE_RATE)
        chime = _tone(1046.50 + float(rng.integers(0, 80)), 0.35, volume=0.04)
        end_s = min(n, idx + len(chime))
        mix[idx:end_s] += chime[: end_s - idx]

    peak = np.max(np.abs(mix)) or 1.0
    mix = mix / peak * 0.88
    fade = int(0.8 * SAMPLE_RATE)
    mix[-fade:] *= np.linspace(1.0, 0.0, fade)

    stereo = np.column_stack((mix, np.roll(mix, 12)))
    out_path = out_path or (ASSETS / "music" / "colourdiam_score.wav")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), stereo[: int(duration * SAMPLE_RATE)], SAMPLE_RATE)
    return out_path
