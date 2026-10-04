import json
import subprocess
from pathlib import Path

from generator.beats import save_beats_csv, track_beats
from generator.brand import ASSETS, FORMATS, FPS, OUTPUT
from generator.campaigns import CAMPAIGNS, get_campaign
from generator.music import generate_brand_score
from generator.render import render_frame


def _encode_video(frames_dir: Path, audio_path: Path, out_mp4: Path, size: tuple[int, int]) -> None:
    w, h = size
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frames_dir / "frame_%05d.jpg"),
        "-i",
        str(audio_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        "-vf",
        f"scale={w}:{h}",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def generate_brand_video(fmt: str = "vertical", campaign: str = "register") -> dict:
    if fmt not in FORMATS:
        raise ValueError(f"Unknown format: {fmt}")
    camp = get_campaign(campaign)
    spec = FORMATS[fmt]
    size = (spec["width"], spec["height"])
    OUTPUT.mkdir(parents=True, exist_ok=True)
    work = OUTPUT / f"work_{campaign}_{fmt}"
    frames_dir = work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    audio_path = generate_brand_score(ASSETS / "music" / "colourdiam_score.wav")
    beat_data = track_beats(audio_path)
    csv_path = save_beats_csv(beat_data["times"], OUTPUT / "beats.csv")

    duration = beat_data["duration"]
    total_frames = int(duration * FPS)
    beats = beat_data["times"]
    for i in range(total_frames):
        t = i / FPS
        frame = render_frame(t, beats, size, campaign)
        frame.save(frames_dir / f"frame_{i:05d}.jpg", quality=88)

    out_mp4 = OUTPUT / f"colourdiam_{campaign}_{fmt}.mp4"
    _encode_video(frames_dir, audio_path, out_mp4, size)
    poster = frames_dir / "frame_00012.jpg"
    poster_out = OUTPUT / f"colourdiam_{campaign}_{fmt}_poster.jpg"
    if poster.exists():
        poster_out.write_bytes(poster.read_bytes())

    caption_path = OUTPUT / f"colourdiam_{campaign}_{fmt}.txt"
    caption_path.write_text(camp["caption"] + "\n\n" + camp["hashtags"] + "\n", encoding="utf-8")
    meta_path = OUTPUT / f"colourdiam_{campaign}_{fmt}.json"
    result = {
        "video": str(out_mp4),
        "poster": str(poster_out) if poster_out.exists() else "",
        "caption": str(caption_path),
        "beats_csv": str(csv_path),
        "audio": str(audio_path),
        "tempo": beat_data["tempo"],
        "beat_count": len(beats),
        "duration": duration,
        "format": fmt,
        "campaign": campaign,
        "cta": camp["primary_cta"],
        "url": camp["url"],
        "size": size,
    }
    meta_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["meta"] = str(meta_path)
    return result


def list_ready_ads() -> list[dict]:
    ads = []
    for campaign in CAMPAIGNS:
        for fmt, spec in FORMATS.items():
            video = OUTPUT / f"colourdiam_{campaign}_{fmt}.mp4"
            poster = OUTPUT / f"colourdiam_{campaign}_{fmt}_poster.jpg"
            if video.exists():
                ads.append(
                    {
                        "campaign": campaign,
                        "format": fmt,
                        "label": f"{campaign.title()} · {spec['label']}",
                        "file": f"/media/{video.name}",
                        "poster": f"/media/{poster.name}" if poster.exists() else "",
                        "size": f"{spec['width']}x{spec['height']}",
                        "cta": CAMPAIGNS[campaign]["primary_cta"],
                        "url": CAMPAIGNS[campaign]["url"],
                    }
                )
    return ads
