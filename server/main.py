from __future__ import annotations

import asyncio
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm import (
    builtin_terms,
    fetch_hotlist,
    fetch_url_text,
    generate_script_with_llm,
    parse_dialogues,
)
from media import (
    STORAGE,
    VOICES,
    aspect_size,
    collect_clips,
    concat_clips,
    cues_from_text,
    ensure_bgm,
    mux_video,
    probe_duration,
    synthesize_dialogues,
    synthesize_voice,
    write_ass,
)

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
TASKS: dict[str, dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()

app = FastAPI(title="MoneyPrinterTurbo", version="1.3.7")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for folder in ("tasks", "uploads", "public"):
    (STORAGE / folder).mkdir(parents=True, exist_ok=True)

app.mount("/files", StaticFiles(directory=str(STORAGE / "tasks")), name="files")


def default_settings() -> dict[str, Any]:
    return {
        "pexels_api_key": "",
        "pixabay_api_key": "",
        "llm_provider": "builtin",
        "llm_base_url": "",
        "llm_api_key": "",
        "llm_model": "",
    }


def load_settings() -> dict[str, Any]:
    settings = default_settings()
    if CONFIG_PATH.exists():
        try:
            settings.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return settings


def save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    settings = load_settings()
    for key in default_settings():
        if key in payload and payload[key] is not None:
            settings[key] = payload[key]
    CONFIG_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return settings


def public_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "subject": task.get("subject", ""),
        "state": task.get("state", 4),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
        "videos": task.get("videos", []),
        "error": task.get("error"),
    }


def update_task(task_id: str, **fields: Any) -> None:
    with TASKS_LOCK:
        TASKS.setdefault(task_id, {"task_id": task_id})
        TASKS[task_id].update(fields)


class ScriptBody(BaseModel):
    video_subject: str = ""
    video_language: str = "auto"
    paragraph_number: int = 1
    video_script_prompt: str = ""
    video_script: str = ""
    video_terms: str = ""
    video_style: str = "narration"
    source_url: str = ""
    article_text: str = ""


class UrlBody(BaseModel):
    url: str


class TermsBody(ScriptBody):
    amount: int = 5


class VoicePreviewBody(BaseModel):
    text: str
    voice_name: str = "zh-CN-XiaoxiaoNeural"
    voice_rate: float = 1.0


class SettingsBody(BaseModel):
    pexels_api_key: str | None = None
    pixabay_api_key: str | None = None
    llm_provider: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None


@app.get("/api/voices")
def list_voices():
    return {"voices": VOICES}


@app.get("/api/settings")
def get_settings():
    return load_settings()


@app.post("/api/settings")
def post_settings(body: SettingsBody):
    return save_settings(body.model_dump())


def resolve_article(source_url: str, article_text: str) -> dict[str, str]:
    text = (article_text or "").strip()
    url = (source_url or "").strip()
    if text:
        title = text.splitlines()[0][:80]
        return {"url": url, "title": title, "content": text[:8000]}
    if url:
        return fetch_url_text(url)
    return {"url": "", "title": "", "content": ""}


@app.get("/api/hotlist")
def hotlist():
    return fetch_hotlist()


@app.post("/api/url-preview")
def url_preview(body: UrlBody):
    try:
        data = fetch_url_text(body.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return data


@app.post("/api/scripts")
def create_script(body: ScriptBody):
    settings = load_settings()
    extra = body.video_script_prompt or ""
    subject = body.video_subject
    article = {"url": "", "title": "", "content": ""}
    try:
        article = resolve_article(body.source_url, body.article_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if article["content"]:
        extra = (extra + "\n" + article["content"]).strip()
        subject = subject or article["title"]
    script = generate_script_with_llm(
        settings,
        subject,
        body.video_language,
        max(1, min(body.paragraph_number, 8)),
        extra,
        body.video_style or "narration",
    )
    terms = builtin_terms(subject, script + " " + article["content"], 5)
    return {
        "video_script": script,
        "video_terms": terms,
        "article_title": article["title"],
        "article_text": article["content"],
        "dialogues": parse_dialogues(script),
    }


@app.post("/api/terms")
def create_terms(body: TermsBody):
    script = body.video_script or body.video_subject
    return {"video_terms": builtin_terms(body.video_subject, script, body.amount or 5)}


@app.post("/api/voice-preview")
async def voice_preview(body: VoicePreviewBody):
    dest = STORAGE / "uploads" / f"preview-{uuid.uuid4().hex}.mp3"
    await synthesize_voice(body.text[:180], body.voice_name, body.voice_rate, dest)
    return FileResponse(dest, media_type="audio/mpeg", filename="preview.mp3")


@app.get("/api/tasks")
def list_tasks():
    with TASKS_LOCK:
        tasks = [public_task(item) for item in reversed(list(TASKS.values()))]
    return {"tasks": tasks, "total": len(tasks)}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return {"status": 200, "data": public_task(task)}


def parse_terms(raw: str, subject: str, script: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[,，\n]+", raw or "") if p.strip()]
    if parts:
        return parts
    return builtin_terms(subject, script, 5)


async def generate_one(task_id: str, params: dict[str, Any], custom_audio: str | None) -> str:
    workdir = STORAGE / "tasks" / task_id
    workdir.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    subject = params.get("video_subject") or "short video"
    language = params.get("video_language") or "auto"
    extra = params.get("video_script_prompt") or ""
    style = (params.get("video_style") or "narration").strip().lower()
    article_text = (params.get("article_text") or "").strip()
    source_url = (params.get("source_url") or "").strip()
    if source_url and not article_text:
        update_task(task_id, progress=6, message="Fetching article")
        article = fetch_url_text(source_url)
        article_text = article["content"]
        subject = subject if params.get("video_subject") else article["title"] or subject
        extra = (extra + "\n" + article_text).strip()
    elif article_text:
        extra = (extra + "\n" + article_text).strip()
    script = (params.get("video_script") or "").strip()
    if not script:
        update_task(task_id, progress=8, message="Writing script")
        script = generate_script_with_llm(
            settings,
            subject,
            language,
            max(1, int(params.get("paragraph_number") or 1)),
            extra,
            style,
        )
    dialogues = parse_dialogues(script)
    terms = parse_terms(params.get("video_terms") or "", subject, script + " " + article_text)
    aspect = params.get("video_aspect") or "9:16"
    width, height = aspect_size(aspect)
    clip_duration = float(params.get("video_clip_duration") or 3)

    voice_path = None
    cues: list[dict[str, Any]] = []
    duration = max(8.0, min(42.0, max(len(script) / 12, 10)))
    if params.get("voice_mode") == "upload" and custom_audio:
        voice_path = custom_audio
        duration = probe_duration(voice_path)
        words = re.findall(r".+?[。！？.!?]|[\s\S]+$", script)
        step = duration / max(1, len(words))
        cues = [{"text": w.strip(), "start": i * step, "end": (i + 1) * step} for i, w in enumerate(words) if w.strip()]
    elif params.get("voice_mode") != "none":
        update_task(task_id, progress=22, message="Synthesizing voiceover")
        voice_file = workdir / "voice.mp3"
        try:
            if dialogues and style in {"podcast", "crosstalk", "talkshow"}:
                voice_path, cues = await synthesize_dialogues(
                    dialogues,
                    params.get("voice_name") or "zh-CN-XiaoxiaoNeural",
                    float(params.get("voice_rate") or 1.0),
                    voice_file,
                )
            else:
                voice_path, cues = await synthesize_voice(
                    script,
                    params.get("voice_name") or "zh-CN-XiaoxiaoNeural",
                    float(params.get("voice_rate") or 1.0),
                    voice_file,
                )
            duration = probe_duration(voice_path)
        except Exception as exc:
            update_task(task_id, progress=28, message=f"Voice fallback: {exc}")
            voice_path = None
            cues = cues_from_text(script, duration)
    else:
        cues = cues_from_text(script, duration)

    update_task(task_id, progress=45, message="Collecting footage")
    clips = collect_clips(terms, workdir, settings, aspect, clip_duration, duration)
    update_task(task_id, progress=68, message="Editing video")
    visual = concat_clips(clips, workdir / "concat.txt", width, height, duration)

    bgm = None
    if (params.get("bgm_type") or "random") != "none":
        bgm = ensure_bgm(workdir / "bgm.mp3", duration)

    ass_file = None
    if params.get("subtitle_enabled", True) and cues:
        ass_file = write_ass(workdir / "subs.ass", cues, width, height, params)

    dest = workdir / "final-1.mp4"
    mux_video(
        visual,
        voice_path,
        bgm,
        ass_file,
        dest,
        float(params.get("voice_volume") or 1.0),
        float(params.get("bgm_volume") or 0.2),
        duration,
    )
    return f"/files/{task_id}/final-1.mp4"


def run_task(task_id: str, params: dict[str, Any], custom_audio: str | None) -> None:
    try:
        update_task(task_id, state=4, progress=4, message="Starting")
        video_url = asyncio.run(generate_one(task_id, params, custom_audio))
        update_task(task_id, state=1, progress=100, message="Complete", videos=[video_url], error=None)
    except Exception as exc:
        import traceback

        traceback.print_exc()
        update_task(task_id, state=-1, progress=0, message="Failed", error=str(exc))


@app.post("/api/videos")
async def create_video(payload: str = Form(...), custom_audio: UploadFile | None = File(None)):
    try:
        params = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid payload") from exc
    if not (
        params.get("video_subject")
        or params.get("video_script")
        or params.get("source_url")
        or params.get("article_text")
    ):
        raise HTTPException(status_code=400, detail="video subject or article URL is required")

    task_id = uuid.uuid4().hex
    audio_path = None
    if custom_audio and custom_audio.filename:
        suffix = Path(custom_audio.filename).suffix or ".mp3"
        audio_path = str(STORAGE / "uploads" / f"{task_id}{suffix}")
        Path(audio_path).write_bytes(await custom_audio.read())

    update_task(
        task_id,
        subject=params.get("video_subject") or params.get("source_url") or "untitled",
        state=4,
        progress=1,
        message="Queued",
        videos=[],
        error=None,
    )
    thread = threading.Thread(target=run_task, args=(task_id, params, audio_path), daemon=True)
    thread.start()
    return {"status": 200, "data": {"task_id": task_id}}


@app.exception_handler(Exception)
async def unhandled_error(_, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/api/health")
def health():
    return {"ok": True}


def serve() -> None:
    import uvicorn

    host = os.environ.get("MPT_LISTEN_HOST", "127.0.0.1")
    port = int(os.environ.get("MPT_LISTEN_PORT", "8080"))
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    serve()
