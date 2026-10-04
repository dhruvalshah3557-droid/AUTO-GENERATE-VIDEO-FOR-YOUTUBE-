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
    looks_like_article_url,
    parse_dialogues,
    pick_hot_topics,
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
LIBRARY_PATH = STORAGE / "public" / "library.json"
USED_TOPICS_PATH = STORAGE / "public" / "used-topics.json"
TASKS: dict[str, dict[str, Any]] = {}
TASKS_LOCK = threading.Lock()
AUTO_LOCK = threading.Lock()
AUTO_STATE: dict[str, Any] = {
    "running": False,
    "batch_id": None,
    "message": "",
    "total": 0,
    "done": 0,
    "task_ids": [],
}

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


def load_json_file(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def save_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def used_topics() -> set[str]:
    raw = load_json_file(USED_TOPICS_PATH, [])
    return {str(item).casefold() for item in raw}


def remember_topic(title: str) -> None:
    topics = load_json_file(USED_TOPICS_PATH, [])
    if title and title not in topics:
        topics.append(title)
        save_json_file(USED_TOPICS_PATH, topics[-200:])


def persist_library() -> None:
    with TASKS_LOCK:
        rows = [public_task(item) for item in TASKS.values()]
    save_json_file(LIBRARY_PATH, rows)


def restore_library() -> None:
    rows = load_json_file(LIBRARY_PATH, [])
    if not isinstance(rows, list):
        return
    with TASKS_LOCK:
        for row in rows:
            task_id = str(row.get("task_id") or "")
            if not task_id:
                continue
            TASKS.setdefault(task_id, {"task_id": task_id})
            TASKS[task_id].update(row)


def public_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "subject": task.get("subject", ""),
        "state": task.get("state", 4),
        "progress": task.get("progress", 0),
        "message": task.get("message", ""),
        "videos": task.get("videos", []),
        "error": task.get("error"),
        "script": task.get("script", ""),
        "video_style": task.get("video_style", "narration"),
        "source_url": task.get("source_url", ""),
        "hot_source": task.get("hot_source", ""),
        "decision": task.get("decision", "pending"),
        "auto": bool(task.get("auto")),
    }


restore_library()


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
    if source_url and not article_text and looks_like_article_url(source_url):
        update_task(task_id, progress=6, message="Fetching article")
        try:
            article = fetch_url_text(source_url)
            article_text = article["content"]
            subject = subject if params.get("video_subject") else article["title"] or subject
            extra = (extra + "\n" + article_text).strip()
        except Exception:
            article_text = ""
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
    update_task(task_id, script=script, subject=subject, source_url=source_url, video_style=style)
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
        persist_library()
    except Exception as exc:
        import traceback

        traceback.print_exc()
        update_task(task_id, state=-1, progress=0, message="Failed", error=str(exc))
        persist_library()


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
    persist_library()
    return {"status": 200, "data": {"task_id": task_id}}


class AutoBatchBody(BaseModel):
    count: int = 3
    hot_source: str = "all"
    video_style: str = "podcast"
    video_language: str = "auto"
    video_aspect: str = "9:16"
    video_clip_duration: int = 3
    voice_mode: str = "auto"
    voice_name: str = "zh-CN-XiaoxiaoNeural"
    voice_rate: float = 1.0
    voice_volume: float = 1.0
    bgm_type: str = "random"
    bgm_volume: float = 0.2
    subtitle_enabled: bool = True
    font_name: str = "NotoSansCJK-Bold.ttc"
    subtitle_position: str = "bottom"
    text_fore_color: str = "#ffffff"
    font_size: int = 60
    stroke_color: str = "#000000"
    stroke_width: float = 1.5
    fetch_article: bool = True


class DecisionBody(BaseModel):
    decision: str


def auto_status() -> dict[str, Any]:
    with AUTO_LOCK:
        return dict(AUTO_STATE)


def queue_auto_task(params: dict[str, Any]) -> str:
    task_id = uuid.uuid4().hex
    update_task(
        task_id,
        subject=params.get("video_subject") or params.get("source_url") or "untitled",
        state=4,
        progress=1,
        message="Queued",
        videos=[],
        error=None,
        script="",
        video_style=params.get("video_style") or "narration",
        source_url=params.get("source_url") or "",
        hot_source=params.get("hot_source") or "",
        decision="pending",
        auto=True,
    )
    thread = threading.Thread(target=run_task, args=(task_id, params, None), daemon=True)
    thread.start()
    return task_id


def run_auto_batch(body: dict[str, Any]) -> None:
    count = max(1, min(int(body.get("count") or 3), 6))
    source = body.get("hot_source") or "all"
    style = body.get("video_style") or "podcast"
    with AUTO_LOCK:
        AUTO_STATE.update({"running": True, "message": "Picking trending topics", "done": 0, "total": count})
    try:
        topics = pick_hot_topics(fetch_hotlist(), source, count, used_topics())
        if not topics:
            raise RuntimeError("no trending topics available")
        task_ids: list[str] = []
        with AUTO_LOCK:
            AUTO_STATE["total"] = len(topics)
            AUTO_STATE["message"] = f"Queued {len(topics)} trending videos"
        for topic in topics:
            article_text = ""
            source_url = topic.get("url") or ""
            if body.get("fetch_article", True) and looks_like_article_url(source_url):
                try:
                    article_text = fetch_url_text(source_url).get("content") or ""
                except Exception:
                    article_text = ""
            params = {
                "video_subject": topic["title"],
                "video_language": body.get("video_language") or "auto",
                "paragraph_number": 3,
                "video_script_prompt": "",
                "video_script": "",
                "video_terms": "",
                "video_style": style,
                "source_url": source_url,
                "article_text": article_text,
                "video_aspect": body.get("video_aspect") or "9:16",
                "video_clip_duration": body.get("video_clip_duration") or 3,
                "voice_mode": body.get("voice_mode") or "auto",
                "voice_name": body.get("voice_name") or "zh-CN-XiaoxiaoNeural",
                "voice_rate": body.get("voice_rate") or 1.0,
                "voice_volume": body.get("voice_volume") or 1.0,
                "bgm_type": body.get("bgm_type") or "random",
                "bgm_volume": body.get("bgm_volume") or 0.2,
                "subtitle_enabled": body.get("subtitle_enabled", True),
                "font_name": body.get("font_name") or "NotoSansCJK-Bold.ttc",
                "subtitle_position": body.get("subtitle_position") or "bottom",
                "text_fore_color": body.get("text_fore_color") or "#ffffff",
                "font_size": body.get("font_size") or 60,
                "stroke_color": body.get("stroke_color") or "#000000",
                "stroke_width": body.get("stroke_width") or 1.5,
                "hot_source": topic.get("source") or source,
            }
            remember_topic(topic["title"])
            task_ids.append(queue_auto_task(params))
            with AUTO_LOCK:
                AUTO_STATE["done"] = len(task_ids)
                AUTO_STATE["task_ids"] = list(task_ids)
                AUTO_STATE["message"] = f"Started {len(task_ids)}/{len(topics)}: {topic['title']}"
        persist_library()
        with AUTO_LOCK:
            AUTO_STATE["running"] = False
            AUTO_STATE["message"] = "Auto batch queued. Preview and keep or skip."
    except Exception as exc:
        with AUTO_LOCK:
            AUTO_STATE["running"] = False
            AUTO_STATE["message"] = f"Auto batch failed: {exc}"


@app.get("/api/auto")
def get_auto():
    return auto_status()


@app.post("/api/auto")
def start_auto(body: AutoBatchBody):
    with AUTO_LOCK:
        if AUTO_STATE.get("running"):
            raise HTTPException(status_code=409, detail="auto batch already running")
        AUTO_STATE.update(
            {
                "running": True,
                "batch_id": uuid.uuid4().hex,
                "message": "Starting auto batch",
                "total": max(1, min(body.count, 6)),
                "done": 0,
                "task_ids": [],
            }
        )
    thread = threading.Thread(target=run_auto_batch, args=(body.model_dump(),), daemon=True)
    thread.start()
    return {"status": 200, "data": auto_status()}


@app.get("/api/library")
def get_library(decision: str = "all"):
    with TASKS_LOCK:
        tasks = [public_task(item) for item in reversed(list(TASKS.values()))]
    if decision and decision != "all":
        tasks = [item for item in tasks if item.get("decision") == decision]
    return {"tasks": tasks, "total": len(tasks), "auto": auto_status()}


@app.post("/api/tasks/{task_id}/decision")
def decide_task(task_id: str, body: DecisionBody):
    decision = (body.decision or "").strip().lower()
    if decision not in {"keep", "skip", "pending"}:
        raise HTTPException(status_code=400, detail="decision must be keep, skip, or pending")
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task not found")
        task["decision"] = decision
        snapshot = public_task(task)
    persist_library()
    return {"status": 200, "data": snapshot}


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
