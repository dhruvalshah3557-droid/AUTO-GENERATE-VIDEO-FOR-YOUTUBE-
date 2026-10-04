from __future__ import annotations

import html as html_lib
import json
import re
import urllib.parse
import urllib.request
from typing import Any

SCRIPT_TEMPLATES = {
    "en": [
        "{subject} is changing how we live, work, and create. In just a few seconds, this idea becomes something you can see, hear, and remember.",
        "First, notice the everyday moments: small tools, quiet routines, and the details most people walk past. That is where the story begins.",
        "Then the pace picks up. New methods, sharper choices, and clearer results turn a simple topic into a short film you can share anywhere.",
        "The takeaway is simple: stay curious, keep the message focused, and let the pictures carry the emotion to the final frame.",
    ],
    "zh": [
        "{subject}正在改变我们观察世界的方式。只需一个明确主题，就能把想法变成可看、可听、可分享的短视频。",
        "先从日常生活切入：熟悉的场景、细微的动作、容易被忽略的细节，会让观众立刻进入故事。",
        "随后加快节奏，用更清晰的画面和更有力的旁白，把信息压缩成短视频该有的密度。",
        "最后留下一句能记住的结论：主题要准，画面要稳，情绪要连贯，成片才会有传播力。",
    ],
}

STYLE_WRITERS = {
    "podcast": (
        "You write a natural two-host podcast dialogue. Speakers are only 小简 (host, vivid stories) "
        "and 老陈 (curious interruptor). Cover every important point from the source. "
        "Output only lines as '小简：...' / '老陈：...'. No title, notes, or stage directions."
    ),
    "crosstalk": (
        "You write a crosstalk (对口相声) routine. 小简 is 逗哏, 老陈 is 捧哏. "
        "Keep the knowledge from the source, add setup-punchline rhythm, spoken Chinese. "
        "Output only lines as '小简：...' / '老陈：...'. No notes or emojis."
    ),
    "talkshow": (
        "You write a first-person standup talkshow monologue for 小简. "
        "Opinion + punchlines + rhythm, 400-800 Chinese characters in 3-5 short paragraphs. "
        "Output only '小简：...' lines. No stage directions."
    ),
}

HOTLIST_FALLBACK = {
    "success": True,
    "data": [
        {
            "name": "36氪",
            "data": [
                {
                    "index": 1,
                    "title": "人工智能如何改变日常生活",
                    "url": "https://36kr.com/",
                    "hot": "hot",
                },
                {
                    "index": 2,
                    "title": "短视频创作者怎样用 AI 提效",
                    "url": "https://36kr.com/",
                    "hot": "hot",
                },
                {
                    "index": 3,
                    "title": "新能源车的下一 milestone",
                    "url": "https://36kr.com/",
                    "hot": "hot",
                },
            ],
        },
        {
            "name": "微博",
            "data": [
                {
                    "index": 1,
                    "title": "今日热点：城市夜景与生活节奏",
                    "url": "https://s.weibo.com/top/summary",
                    "hot": "hot",
                },
                {
                    "index": 2,
                    "title": "年轻人的周末去哪玩",
                    "url": "https://s.weibo.com/top/summary",
                    "hot": "hot",
                },
            ],
        },
        {
            "name": "知乎",
            "data": [
                {
                    "index": 1,
                    "title": "如果只用三分钟讲清一个复杂概念",
                    "url": "https://www.zhihu.com/",
                    "hot": "hot",
                },
                {
                    "index": 2,
                    "title": "怎样把长文章改成播客对话",
                    "url": "https://www.zhihu.com/",
                    "hot": "hot",
                },
            ],
        },
    ],
}


def _detect_language(text: str, preferred: str) -> str:
    if preferred and preferred != "auto":
        return preferred
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    return "en"


def _paragraphs_for(subject: str, language: str, count: int, extra: str) -> list[str]:
    lines = SCRIPT_TEMPLATES["zh" if language.startswith("zh") else "en"]
    filled = [line.format(subject=subject.strip() or "this topic") for line in lines]
    if extra:
        filled.insert(1, extra.strip()[:480])
    while len(filled) < count:
        filled.append(filled[-1])
    return filled[: max(1, count)]


def builtin_script(subject: str, language: str, paragraphs: int, extra: str) -> str:
    lang = _detect_language(subject + " " + (extra or ""), language)
    return "\n".join(_paragraphs_for(subject, lang, paragraphs, extra))


def builtin_terms(subject: str, script: str, amount: int = 5) -> list[str]:
    blob = f"{subject} {script}".lower()
    blob = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", blob)
    stop = {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "from",
        "your",
        "into",
        "will",
        "are",
        "was",
        "you",
        "our",
        "can",
        "how",
        "video",
        "short",
        "speaker",
        "content",
        "小简",
        "老陈",
    }
    words = [w for w in blob.split() if len(w) > 2 and w not in stop]
    unique: list[str] = []
    for word in words:
        if word not in unique:
            unique.append(word)
    seeds = unique[: max(3, amount)]
    extras = ["cinematic b-roll", "city lights", "nature landscape", "people working", "close up details"]
    while len(seeds) < amount:
        seeds.append(extras[len(seeds) % len(extras)])
    return seeds[:amount]


def _sentences(text: str, limit: int = 8) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[。！？.!?])\s*", text or "") if p.strip()]
    cleaned = [re.sub(r"\s+", " ", p)[:160] for p in parts if len(p) > 8]
    if cleaned:
        return cleaned[:limit]
    blob = re.sub(r"\s+", " ", text or "").strip()
    if blob:
        return [blob[:160]]
    return []


def _source_bits(subject: str, extra: str) -> list[str]:
    bits = _sentences(extra, 8)
    if not bits:
        bits = _sentences(subject, 4)
    if not bits:
        bits = [subject.strip() or "short video"]
    while len(bits) < 4:
        bits.append(bits[-1])
    return bits[:6]


def builtin_style_script(subject: str, language: str, extra: str, style: str) -> str:
    lang = _detect_language(subject + " " + (extra or ""), language)
    bits = _source_bits(subject, extra)
    topic = subject.strip() or bits[0][:24]
    if style == "talkshow":
        if lang.startswith("zh"):
            return "\n".join(
                [
                    f"小简：今天咱们不讲大道理，就说{topic}。这事儿听着挺正经，其实每个人每天都在被它推着走。",
                    f"小简：你看啊，{bits[0]} 说白了，就是把复杂的东西塞进三分钟里，还得让人愿意看完。",
                    f"小简：然后节奏一加快，{bits[1]} 立刻变成段子素材。不是因为它有多玄，是因为它太日常了。",
                    f"小简：最后记住一句就行：主题要准，包袱要稳，{topic}才能从文章变成能发出去的短视频。",
                ]
            )
        return "\n".join(
            [
                f"Alex: Let's talk about {topic} like we're on stage, not in a classroom.",
                f"Alex: First beat: {bits[0]}",
                f"Alex: Then the turn: {bits[1]} That is the punchline hiding in plain sight.",
                f"Alex: Takeaway: keep it sharp, keep it human, and let {topic} travel as a short.",
            ]
        )
    host, guest = ("小简", "老陈") if lang.startswith("zh") else ("Alex", "Chris")
    if style == "crosstalk":
        if lang.startswith("zh"):
            return "\n".join(
                [
                    f"小简：今儿咱不说别的，就说{topic}。",
                    "老陈：哟，这题目够大，您能讲明白吗？",
                    f"小简：能。先听这个：{bits[0]}",
                    "老陈：这不就是把文章往短视频里塞吗？",
                    f"小简：对，但得有包袱。{bits[1]}",
                    "老陈：那观众听完能记住啥？",
                    f"小简：记住三件事：画面要准，声音要稳，{bits[2]}",
                    "老陈：行，这回我服了。下回还讲这个？",
                    f"小简：讲。{topic}这题，越日常越好笑。",
                ]
            )
        return "\n".join(
            [
                f"{host}: Tonight's bit is {topic}.",
                f"{guest}: That's a big swing. You sure?",
                f"{host}: Watch this: {bits[0]}",
                f"{guest}: So we stuffed an article into a short?",
                f"{host}: With a punchline. {bits[1]}",
                f"{guest}: And the audience remembers...?",
                f"{host}: Picture, voice, and {bits[2]}",
            ]
        )
    if lang.startswith("zh"):
        return "\n".join(
            [
                f"小简：你有没有想过，{topic}其实就藏在日常里，只是很少有人把它讲清楚。",
                "老陈：啊哈，那你今天是要把文章变成聊天？",
                f"小简：对。先从这儿开始：{bits[0]}",
                f"老陈：所以重点不是堆信息，是让人听进去？",
                f"小简：没错。接着是：{bits[1]}",
                f"老陈：那要是时间只够三分钟呢？",
                f"小简：那就抓住这一句：{bits[2]}",
                f"老陈：我懂了，最后再给一个能带走的结论。",
                f"小简：结论就是：把{topic}讲成人话，画面和声音会帮你把情绪送到最后一帧。",
            ]
        )
    return "\n".join(
        [
            f"{host}: Have you noticed how {topic} hides in ordinary days?",
            f"{guest}: So this is the article, but as a conversation?",
            f"{host}: Exactly. Start here: {bits[0]}",
            f"{guest}: Not more facts, just something you can hear.",
            f"{host}: Next beat: {bits[1]}",
            f"{guest}: And if we only have three minutes?",
            f"{host}: Keep this: {bits[2]}",
            f"{guest}: Then land the takeaway.",
            f"{host}: Make {topic} human, and let the pictures carry it home.",
        ]
    )


def parse_dialogues(script: str) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    pattern = re.compile(r"^(小简|老陈|Alex|Chris)[:：]\s*(.+)$")
    for raw in (script or "").splitlines():
        text = raw.strip()
        if not text:
            continue
        match = pattern.match(text)
        if match:
            lines.append({"speaker": match.group(1), "content": match.group(2).strip()})
        elif lines:
            lines[-1]["content"] += " " + text
    return [item for item in lines if item["content"]]


def script_from_dialogues(dialogues: list[dict[str, str]]) -> str:
    return "\n".join(f"{item['speaker']}：{item['content']}" for item in dialogues)


def looks_like_article_url(url: str) -> bool:
    if not is_public_http_url(url):
        return False
    parsed = urllib.parse.urlparse(url.strip())
    path = (parsed.path or "").rstrip("/")
    return bool(path) and path != ""


def flatten_hotlist(payload: dict[str, Any], source: str = "all") -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    wanted = (source or "all").strip()
    for group in payload.get("data") or []:
        name = str(group.get("name") or "").strip()
        if wanted not in {"", "all"} and name != wanted:
            continue
        for row in group.get("data") or []:
            title = str(row.get("title") or row.get("name") or "").strip()
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "url": str(row.get("url") or row.get("link") or "").strip(),
                    "source": name,
                    "hot": str(row.get("hot") or row.get("hotval") or ""),
                }
            )
    return items


def pick_hot_topics(payload: dict[str, Any], source: str, count: int, used: set[str]) -> list[dict[str, str]]:
    items = flatten_hotlist(payload, source)
    fresh = [item for item in items if item["title"].casefold() not in used]
    pool = fresh or items
    picked: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in pool:
        key = item["title"].casefold()
        if key in seen:
            continue
        seen.add(key)
        picked.append(item)
        if len(picked) >= count:
            break
    return picked


def is_public_http_url(url: str) -> bool:
    parsed = urllib.parse.urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return False
    if host.endswith(".local"):
        return False
    if re.match(r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.|169\.254\.)", host):
        return False
    return True


def _strip_html(raw: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|noscript|svg|iframe).*?>.*?</\1>", " ", raw)
    cleaned = re.sub(r"(?is)<!--.*?-->", " ", cleaned)
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", cleaned)
    title = html_lib.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip() if title_match else ""
    text = re.sub(r"(?is)<(br|p|div|h1|h2|h3|li|tr)[^>]*>", "\n", cleaned)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    text = text.strip()
    if title and title.lower() not in text.lower()[:200]:
        text = f"{title}\n{text}"
    lowered = text.lower()
    if any(marker in lowered for marker in ("安全检测", "captcha", "access denied", "just a moment")):
        raise ValueError("article page is blocked or empty")
    return text[:8000]


def fetch_url_text(url: str, timeout: int = 18) -> dict[str, str]:
    if not is_public_http_url(url):
        raise ValueError("only public http(s) article URLs are supported")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MoneyPrinterTurbo/1.3.7)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        payload = resp.read(1_200_000)
        final_url = resp.geturl()
    try:
        decoded = payload.decode(charset, errors="ignore")
    except LookupError:
        decoded = payload.decode("utf-8", errors="ignore")
    text = _strip_html(decoded)
    if len(text) < 40:
        raise ValueError("could not extract article text from URL")
    first = text.splitlines()[0][:80]
    return {"url": final_url, "title": first, "content": text}


def fetch_hotlist() -> dict[str, Any]:
    req = urllib.request.Request(
        "https://api.vvhan.com/api/hotlist/all",
        headers={"User-Agent": "MoneyPrinterTurbo/1.3.7"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict) and data.get("data"):
            return data
    except Exception:
        pass
    return HOTLIST_FALLBACK


def _chat_complete(settings: dict[str, Any], system_prompt: str, user_prompt: str) -> str:
    body = {
        "model": settings.get("llm_model") or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
    }
    url = (settings.get("llm_base_url") or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings['llm_api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return (payload["choices"][0]["message"]["content"] or "").strip()


def generate_script_with_llm(
    settings: dict[str, Any],
    subject: str,
    language: str,
    paragraphs: int,
    extra: str,
    style: str = "narration",
) -> str:
    style = (style or "narration").strip().lower()
    if style not in STYLE_WRITERS:
        style = "narration"
    source = extra.strip() if extra else subject
    if settings.get("llm_provider") != "openai" or not settings.get("llm_api_key"):
        if style == "narration":
            return builtin_script(subject, language, paragraphs, extra)
        return builtin_style_script(subject, language, extra, style)

    lang = _detect_language(subject + " " + (extra or ""), language)
    try:
        if style == "narration":
            prompt = (
                f"Write a spoken narration for a {paragraphs}-paragraph short video about: {subject}. "
                f"Language: {lang}. Style: vivid, concise, suitable for voiceover. "
                f"Return only the narration text. Extra instruction or article: {source or 'none'}"
            )
            text = _chat_complete(settings, "You write short-video voiceover scripts.", prompt)
            return text or builtin_script(subject, language, paragraphs, extra)
        prompt = (
            f"Language: {lang}. Topic: {subject}.\n"
            f"Rewrite the following source into the requested format.\n\n{source}"
        )
        text = _chat_complete(settings, STYLE_WRITERS[style], prompt)
        if text and parse_dialogues(text):
            return script_from_dialogues(parse_dialogues(text))
        if text:
            return text
    except Exception:
        pass
    if style == "narration":
        return builtin_script(subject, language, paragraphs, extra)
    return builtin_style_script(subject, language, extra, style)
