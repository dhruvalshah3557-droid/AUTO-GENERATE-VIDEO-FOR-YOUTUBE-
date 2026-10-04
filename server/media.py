from __future__ import annotations

import json
import math
import os
import random
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORAGE = ROOT / "storage"
FONT_MAP = {
    "NotoSansCJK-Bold.ttc": "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "NotoSansCJK-Regular.ttc": "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "DejaVuSans-Bold.ttf": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

VOICES = [
    {"id": "zh-CN-XiaoxiaoNeural", "label": "zh-CN-Xiaoxiao-Female"},
    {"id": "zh-CN-YunxiNeural", "label": "zh-CN-Yunxi-Male"},
    {"id": "zh-CN-YunyangNeural", "label": "zh-CN-Yunyang-Male"},
    {"id": "en-US-JennyNeural", "label": "en-US-Jenny-Female"},
    {"id": "en-US-GuyNeural", "label": "en-US-Guy-Male"},
    {"id": "en-GB-SoniaNeural", "label": "en-GB-Sonia-Female"},
    {"id": "ja-JP-NanamiNeural", "label": "ja-JP-Nanami-Female"},
    {"id": "ko-KR-SunHiNeural", "label": "ko-KR-SunHi-Female"},
]

SPEAKER_VOICES = {
    "小简": "zh-CN-XiaoxiaoNeural",
    "老陈": "zh-CN-YunxiNeural",
    "Alex": "en-US-JennyNeural",
    "Chris": "en-US-GuyNeural",
}


def run(cmd: list[str], timeout: int = 120) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:] or result.stdout[-2000:] or "command failed")


def probe_duration(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        return max(0.1, float(result.stdout.strip()))
    except ValueError:
        return 3.0


def aspect_size(aspect: str) -> tuple[int, int]:
    return {"16:9": (1920, 1080), "1:1": (1080, 1080)}.get(aspect, (1080, 1920))


def font_path(name: str) -> str:
    return FONT_MAP.get(name, FONT_MAP["NotoSansCJK-Bold.ttc"])


def _http_json(url: str, headers: dict | None = None, timeout: int = 20) -> dict | list:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "MoneyPrinterTurbo/1.3.7"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download(url: str, dest: Path, timeout: int = 45) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MoneyPrinterTurbo/1.3.7"})
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as fh:
            fh.write(resp.read())
        return dest.exists() and dest.stat().st_size > 10000
    except Exception:
        return False


def search_pexels(query: str, api_key: str, orientation: str) -> list[str]:
    if not api_key:
        return []
    q = urllib.parse.urlencode({"query": query, "per_page": 8, "orientation": orientation})
    try:
        data = _http_json(
            f"https://api.pexels.com/videos/search?{q}",
            headers={"Authorization": api_key},
        )
    except Exception:
        return []
    urls: list[str] = []
    for item in data.get("videos", []):
        files = sorted(item.get("video_files", []), key=lambda x: x.get("width") or 0, reverse=True)
        for media in files:
            link = media.get("link")
            if link and str(media.get("file_type", "")).endswith("mp4"):
                urls.append(link)
                break
    return urls


def search_wikimedia(query: str) -> list[str]:
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:video {query}",
            "gsrlimit": "6",
            "gsrnamespace": "6",
            "prop": "imageinfo",
            "iiprop": "url|mime",
        }
    )
    try:
        data = _http_json(f"https://commons.wikimedia.org/w/api.php?{q}")
    except Exception:
        return []
    urls: list[str] = []
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("url") or ""
        mime = info.get("mime") or ""
        if url and ("video" in mime or url.endswith(".webm") or url.endswith(".mp4")):
            urls.append(url)
    return urls


def make_fallback_clip(dest: Path, width: int, height: int, duration: float, title: str, index: int) -> str:
    colors = ["0x1b3a4b", "0x3d1f4a", "0x1f4b3a", "0x4a2c1f", "0x24344d", "0x3a2a1b"]
    color = colors[index % len(colors)]
    safe_title = re.sub(r"[:\\'\[\]]", " ", title)[:28] or "MoneyPrinterTurbo"
    font = FONT_MAP["NotoSansCJK-Bold.ttc"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    fontsize = max(36, width // 18)
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:d={duration:.2f}:r=30",
            "-vf",
            (
                f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.18:t=fill,"
                f"drawbox=x=72:y=ih/2-90:w=iw-144:h=6:color=white@0.55:t=fill,"
                f"drawtext=fontfile={font}:text='{safe_title}':fontsize={fontsize}:"
                f"fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
            ),
            "-t",
            f"{duration:.2f}",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(dest),
        ],
        timeout=60,
    )
    return str(dest)


def collect_clips(
    terms: list[str],
    workdir: Path,
    settings: dict,
    aspect: str,
    clip_duration: float,
    total_duration: float,
) -> list[str]:
    width, height = aspect_size(aspect)
    orientation = "portrait" if aspect == "9:16" else "landscape" if aspect == "16:9" else "square"
    urls: list[str] = []
    queries = terms or ["cinematic"]
    for query in queries[:6]:
        urls.extend(search_pexels(query, settings.get("pexels_api_key") or "", orientation))
        if len(urls) >= 8:
            break
    if len(urls) < 3:
        for query in queries[:4]:
            urls.extend(search_wikimedia(query))
            if len(urls) >= 6:
                break

    clips: list[str] = []
    needed = max(1, math.ceil(total_duration / max(1.0, clip_duration)))
    unique_urls = list(dict.fromkeys(urls))
    random.shuffle(unique_urls)
    for idx, url in enumerate(unique_urls[: needed + 2]):
        dest = workdir / f"raw-{idx}.mp4"
        if _download(url, dest):
            trimmed = workdir / f"clip-{idx}.mp4"
            try:
                scale = (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},fps=30,setsar=1"
                )
                run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(dest),
                        "-t",
                        f"{clip_duration:.2f}",
                        "-vf",
                        scale,
                        "-an",
                        "-pix_fmt",
                        "yuv420p",
                        str(trimmed),
                    ],
                    timeout=90,
                )
                clips.append(str(trimmed))
            except Exception:
                continue
        if sum(probe_duration(p) for p in clips) >= total_duration:
            break

    idx = len(clips)
    while sum(probe_duration(p) for p in clips) < total_duration or not clips:
        title = queries[idx % len(queries)]
        dest = workdir / f"gen-{idx}.mp4"
        clips.append(make_fallback_clip(dest, width, height, clip_duration, title, idx))
        idx += 1
        if idx > needed + 6:
            break
    return clips


def concat_clips(clips: list[str], dest: Path, width: int, height: int, duration: float) -> str:
    list_file = dest.with_suffix(".txt")
    lines = []
    for clip in clips:
        lines.append(f"file '{clip}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")
    stretched = dest.with_name("visual.mp4")
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30,setsar=1",
            "-t",
            f"{duration:.2f}",
            "-an",
            "-pix_fmt",
            "yuv420p",
            str(stretched),
        ],
        timeout=120,
    )
    return str(stretched)


def ensure_bgm(dest: Path, duration: float) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=196:duration={duration:.2f}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=246.94:duration={duration:.2f}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=293.66:duration={duration:.2f}",
            "-filter_complex",
            "amix=inputs=3:duration=longest,volume=0.18,afade=t=in:st=0:d=1,afade=t=out:st="
            f"{max(0.5, duration - 1.2):.2f}:d=1.2",
            "-t",
            f"{duration:.2f}",
            str(dest),
        ],
        timeout=40,
    )
    return str(dest)


def write_ass(
    dest: Path,
    cues: list[dict],
    width: int,
    height: int,
    params: dict,
) -> str:
    font_file = Path(font_path(params.get("font_name") or "")).name
    font = "Noto Sans CJK SC" if "Noto" in font_file else "DejaVu Sans"
    font_size = int(params.get("font_size") or 60)
    primary = (params.get("text_fore_color") or "#FFFFFF").lstrip("#")
    outline = (params.get("stroke_color") or "#000000").lstrip("#")
    bg = params.get("text_background_color")
    alignment = {"top": 8, "center": 5}.get(params.get("subtitle_position") or "bottom", 2)
    back = "00000000"
    border_style = 1
    if bg:
        color = str(bg).lstrip("#")
        if len(color) == 6:
            back = f"AA{color[4:6]}{color[2:4]}{color[0:2]}"
            border_style = 3
    primary_ass = f"&H00{primary[4:6]}{primary[2:4]}{primary[0:2]}"
    outline_ass = f"&H00{outline[4:6]}{outline[2:4]}{outline[0:2]}"
    border = float(params.get("stroke_width") or 1.5)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary_ass},{outline_ass},&H{back},-1,0,{border_style},{border},0,{alignment},40,40,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(seconds: float) -> str:
        seconds = max(0.0, seconds)
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    events = []
    for cue in cues:
        text = str(cue["text"]).replace("\n", "\\N")
        events.append(f"Dialogue: 0,{ts(cue['start'])},{ts(cue['end'])},Default,,0,0,0,,{text}")
    dest.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return str(dest)


def mux_video(
    visual: str,
    voice: str | None,
    bgm: str | None,
    ass_file: str | None,
    dest: Path,
    voice_vol: float,
    bgm_vol: float,
    duration: float,
) -> str:
    cmd = ["ffmpeg", "-y", "-i", visual]
    filters: list[str] = []
    next_index = 1
    voice_idx = bgm_idx = None
    if voice:
        cmd += ["-i", voice]
        voice_idx = next_index
        next_index += 1
    if bgm:
        cmd += ["-i", bgm]
        bgm_idx = next_index
        next_index += 1
    if not voice and not bgm:
        cmd += ["-f", "lavfi", "-t", f"{duration:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        silent_idx = next_index
    else:
        silent_idx = None

    if ass_file:
        escaped = ass_file.replace("\\", "\\\\").replace(":", "\\:").replace(",", "\\,")
        filters.append(f"[0:v]ass={escaped}:fontsdir=/usr/share/fonts[v]")
        video_map = "[v]"
    else:
        video_map = "0:v"

    mixed = []
    if voice_idx is not None:
        filters.append(f"[{voice_idx}:a]volume={voice_vol}[va]")
        mixed.append("[va]")
    if bgm_idx is not None:
        filters.append(f"[{bgm_idx}:a]volume={bgm_vol}[ba]")
        mixed.append("[ba]")
    if len(mixed) == 2:
        filters.append("[va][ba]amix=inputs=2:duration=first:dropout_transition=2[aout]")
        audio_map = "[aout]"
    elif mixed:
        audio_map = mixed[0]
    else:
        audio_map = f"{silent_idx}:a"

    if filters:
        cmd += ["-filter_complex", ";".join(filters)]
    cmd += [
        "-map",
        video_map,
        "-map",
        audio_map,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-t",
        f"{duration:.2f}",
        str(dest),
    ]
    run(cmd, timeout=180)
    return str(dest)


def _normalize_voice(voice: str) -> str:
    raw = (voice or "").strip()
    if not raw:
        return "zh-CN-XiaoxiaoNeural"
    aliases = {item["label"]: item["id"] for item in VOICES}
    if raw in aliases:
        return aliases[raw]
    known = {item["id"] for item in VOICES}
    if raw in known:
        return raw
    return "zh-CN-XiaoxiaoNeural"


def cues_from_text(text: str, total: float) -> list[dict]:
    parts = [p.strip() for p in re.split(r"(?<=[。！？.!?])\s*", text) if p.strip()]
    if not parts:
        parts = [text.strip() or "MoneyPrinterTurbo"]
    step = max(total, 1.0) / len(parts)
    return [{"text": part, "start": i * step, "end": (i + 1) * step} for i, part in enumerate(parts)]


async def synthesize_voice(text: str, voice: str, rate: float, dest: Path) -> tuple[str, list[dict]]:
    import edge_tts

    voice_id = _normalize_voice(voice)
    rate_pct = int(round((float(rate or 1.0) - 1.0) * 100))
    rate_arg = f"{rate_pct:+d}%"
    communicate = edge_tts.Communicate(text, voice_id, rate=rate_arg)
    cues: list[dict] = []
    chunks: list[bytes] = []
    async for item in communicate.stream():
        if item["type"] == "audio":
            chunks.append(item["data"])
        elif item["type"] in {"WordBoundary", "SentenceBoundary"}:
            start = item["offset"] / 10_000_000
            duration = item["duration"] / 10_000_000
            cues.append({"text": item.get("text") or "", "start": start, "end": start + duration})
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"".join(chunks))
    if dest.stat().st_size < 100:
        raise RuntimeError("voice synthesis returned empty audio")
    total = max(probe_duration(str(dest)), 1.0)
    if not cues:
        return str(dest), cues_from_text(text, total)
    sentences: list[dict] = []
    buf: list[str] = []
    start = cues[0]["start"]
    for cue in cues:
        buf.append(cue["text"])
        joined = " ".join(buf).strip()
        if cue["text"].endswith((".", "!", "?", "。", "！", "？", ",", "，")) or len(joined) > 18:
            sentences.append({"text": joined, "start": start, "end": cue["end"]})
            buf = []
            start = cue["end"]
    if buf:
        sentences.append({"text": " ".join(buf).strip(), "start": start, "end": cues[-1]["end"]})
    return str(dest), sentences or cues_from_text(text, total)


async def synthesize_dialogues(
    dialogues: list[dict],
    default_voice: str,
    rate: float,
    dest: Path,
) -> tuple[str, list[dict]]:
    if not dialogues:
        return await synthesize_voice("MoneyPrinterTurbo", default_voice, rate, dest)

    work = dest.parent / "voices"
    work.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    cues: list[dict] = []
    cursor = 0.0
    pause = 0.18
    for index, item in enumerate(dialogues):
        speaker = str(item.get("speaker") or "")
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        voice = SPEAKER_VOICES.get(speaker) or default_voice
        clip = work / f"line-{index:03d}.mp3"
        try:
            path, line_cues = await synthesize_voice(content, voice, rate, clip)
        except Exception:
            continue
        duration = probe_duration(path)
        label = f"{speaker}：{content}" if speaker else content
        if line_cues:
            for cue in line_cues:
                cues.append(
                    {
                        "text": f"{speaker}：{cue['text']}" if speaker else cue["text"],
                        "start": cursor + float(cue["start"]),
                        "end": cursor + float(cue["end"]),
                    }
                )
        else:
            cues.append({"text": label, "start": cursor, "end": cursor + duration})
        parts.append(path)
        cursor += duration + pause

    if not parts:
        joined = " ".join(str(item.get("content") or "") for item in dialogues)
        return await synthesize_voice(joined or "MoneyPrinterTurbo", default_voice, rate, dest)

    list_file = work / "concat.txt"
    list_file.write_text("\n".join(f"file '{path}'" for path in parts), encoding="utf-8")
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(dest),
        ],
        timeout=90,
    )
    total = probe_duration(str(dest))
    if not cues:
        joined = "\n".join(
            f"{item.get('speaker', '')}：{item.get('content', '')}".strip("：") for item in dialogues
        )
        return str(dest), cues_from_text(joined, total)
    return str(dest), cues
