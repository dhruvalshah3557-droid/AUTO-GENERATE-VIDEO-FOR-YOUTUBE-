import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from generator.brand import (
    BRAND,
    CREAM,
    DIAMOND_COLORS,
    FONTS,
    GOLD,
    GOLD_LIGHT,
    IMG_FANCY,
    IMG_RING,
    INK,
    SOFT_WHITE,
)
from generator.campaigns import get_campaign


def _font(key: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONTS.get(key)
    if path and Path(path).is_file():
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _scaled(base: int, w: int, h: int) -> int:
    return max(12, int(base * min(w, h) / 720))


def _cover(path: Path, size: tuple[int, int], zoom: float = 1.0, pan: float = 0.0) -> Image.Image:
    tw, th = size
    if not path.exists():
        fallback = Image.new("RGBA", (tw, th), (*INK, 255))
        draw = ImageDraw.Draw(fallback)
        draw.ellipse((tw * 0.28, th * 0.28, tw * 0.72, th * 0.72), fill=(232, 160, 184, 180))
        return fallback
    img = Image.open(path).convert("RGBA")
    scale = max(tw / max(img.width, 1), th / max(img.height, 1)) * max(zoom, 1.0)
    nw, nh = max(tw, int(img.width * scale)), max(th, int(img.height * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    pan = max(-1.0, min(1.0, pan))
    x = int(max(0, min(nw - tw, (nw - tw) * (0.5 + pan * 0.18))))
    y = int(max(0, min(nh - th, (nh - th) * 0.5)))
    return img.crop((x, y, x + tw, y + th))


def _fit_text(text: str, font_key: str, max_size: int, min_size: int, max_width: int, w: int, h: int):
    size = max_size
    while size >= min_size:
        font = _font(font_key, _scaled(size, w, h))
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        bbox = probe.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return _font(font_key, _scaled(min_size, w, h))


def _wrap_lines(text: str, font, max_width: int, max_lines: int = 3) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        bbox = probe.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def _center(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill, width: int):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) / 2, y), text, font=font, fill=fill)


def _center_block(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill, width: int, gap: int = 8):
    lines = _wrap_lines(text, font, int(width * 0.86))
    for i, line in enumerate(lines):
        _center(draw, line, font, y + i * (_scaled(34, width, width) + gap), fill, width)
    return len(lines)


def _vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    w, h = img.size
    overlay = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-int(w * 0.15), -int(h * 0.12), int(w * 1.15), int(h * 1.12)), fill=255)
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(8, min(w, h) // 8)))
    dark = Image.new("RGBA", (w, h), (*INK, int(255 * strength)))
    mask = ImageEnhance.Brightness(overlay).enhance(1.0)
    return Image.composite(img, dark, mask)


def _octagon_points(cx: float, cy: float, r: float, rotation: float):
    pts = []
    for i in range(8):
        a = math.radians(rotation + i * 45.0 - 22.5)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _draw_mark(canvas: Image.Image, cx: int, cy: int, radius: int, rotation: float, pulse: float):
    draw = ImageDraw.Draw(canvas, "RGBA")
    colors = [c[1] for c in DIAMOND_COLORS]
    outer = _octagon_points(cx, cy, radius * (0.92 + pulse * 0.08), rotation)
    inner = _octagon_points(cx, cy, radius * 0.42, rotation)
    for i in range(8):
        nxt = (i + 1) % 8
        poly = [outer[i], outer[nxt], inner[nxt], inner[i]]
        col = colors[i % len(colors)]
        draw.polygon(poly, fill=(*col, 235))
    draw.polygon(inner, fill=(0, 0, 0, 255))


def _url_bar(img: Image.Image, url: str) -> None:
    w, h = img.size
    bar_h = max(36, _scaled(42, w, h))
    bar = Image.new("RGBA", (w, bar_h), (10, 10, 10, 170))
    img.alpha_composite(bar, (0, 0))
    draw = ImageDraw.Draw(img)
    font = _fit_text(url.upper(), "sans", 13, 10, int(w * 0.92), w, h)
    _center(draw, url.upper(), font, max(8, bar_h // 4), GOLD, w)


def _scene_logo(w: int, h: int, t: float, beat: float, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    pulse = 0.5 + 0.5 * math.sin(beat * math.pi)
    rot = t * 8.0
    _draw_mark(img, w // 2, int(h * 0.36), int(min(w, h) * 0.14), rot, pulse)
    draw = ImageDraw.Draw(img)
    _center(draw, "COLOUR DIAM", _font("serif", _scaled(48, w, h)), int(h * 0.58), GOLD_LIGHT, w)
    _center(draw, BRAND["since"].upper(), _font("sans_light", _scaled(16, w, h)), int(h * 0.65), GOLD, w)
    _center_block(draw, campaign["hook"], _font("serif_italic", _scaled(22, w, h)), int(h * 0.74), CREAM, w)
    return img


def _scene_hook(w: int, h: int, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    draw = ImageDraw.Draw(img)
    _center(draw, campaign["hook"].upper(), _font("sans_light", _scaled(14, w, h)), int(h * 0.28), GOLD, w)
    headline_font = _fit_text(campaign["headline"], "serif", 34, 18, int(w * 0.86), w, h)
    lines = _center_block(draw, campaign["headline"], headline_font, int(h * 0.38), CREAM, w)
    y = int(h * 0.38) + lines * (_scaled(34, w, h) + 10) + 18
    draw.line((w * 0.28, y, w * 0.72, y), fill=GOLD, width=1)
    _center_block(draw, campaign["promise"], _font("sans_light", _scaled(15, w, h)), y + 18, SOFT_WHITE, w)
    return img


def _scene_image(path: Path, caption: str, sub: str, w: int, h: int, t: float) -> Image.Image:
    zoom = 1.08 + 0.06 * (t % 4) / 4.0
    pan = math.sin(t * 0.35)
    img = _cover(path, (w, h), zoom=zoom, pan=pan)
    img = _vignette(img, 0.62)
    draw = ImageDraw.Draw(img)
    _center_block(draw, caption, _font("serif", _scaled(32, w, h)), int(h * 0.72), CREAM, w)
    _center(draw, sub, _font("sans_light", _scaled(15, w, h)), int(h * 0.84), GOLD_LIGHT, w)
    return img


def _scene_colors(w: int, h: int, beat: float) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    draw = ImageDraw.Draw(img)
    _center(draw, "FANCY COLOUR DIAMONDS", _font("sans_light", _scaled(14, w, h)), int(h * 0.12), GOLD, w)
    _center_block(draw, "Nature's Rarest Palette", _font("serif", _scaled(30, w, h)), int(h * 0.17), CREAM, w)
    cols = 4 if w >= h else 2 if min(w, h) < 500 else 4
    if w < h:
        cols = 4
    gap = max(10, int(w * 0.02))
    box = int((w - gap * (cols + 1)) / cols)
    box = max(36, min(box, int(h * 0.16)))
    top = int(h * 0.34)
    idx = int(beat) % len(DIAMOND_COLORS)
    for i, (name, color) in enumerate(DIAMOND_COLORS):
        r, c = i // cols, i % cols
        x = gap + c * (box + gap)
        y = top + r * (box + max(40, _scaled(48, w, h)))
        rbox = [x, y, x + box, y + box]
        if i == idx:
            draw.rounded_rectangle(
                [x - 4, y - 4, x + box + 4, y + box + 4],
                radius=max(8, box // 2),
                outline=GOLD,
                width=2,
            )
        draw.ellipse(rbox, fill=color)
        label_font = _font("sans", _scaled(12, w, h))
        bbox = draw.textbbox((0, 0), name.upper(), font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (x + (box - tw) / 2, y + box + 8),
            name.upper(),
            font=label_font,
            fill=GOLD_LIGHT if i == idx else SOFT_WHITE,
        )
    return img


def _scene_trust(w: int, h: int, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    draw = ImageDraw.Draw(img)
    _center(draw, "WHY COLOUR DIAM", _font("sans_light", _scaled(14, w, h)), int(h * 0.18), GOLD, w)
    _center_block(draw, campaign["trust"], _font("serif", _scaled(24, w, h)), int(h * 0.26), CREAM, w)
    points = [
        ("GIA", "Certified stones"),
        ("1984", "Family legacy"),
        ("100%", "Money back"),
    ]
    y = int(h * 0.56)
    gap = w // 3
    for i, (year, label) in enumerate(points):
        cx = gap * i + gap // 2
        year_font = _font("serif", _scaled(22, w, h))
        bbox = draw.textbbox((0, 0), year, font=year_font)
        draw.text((cx - (bbox[2] - bbox[0]) / 2, y), year, font=year_font, fill=GOLD)
        label_font = _font("sans_light", _scaled(13, w, h))
        bbox2 = draw.textbbox((0, 0), label, font=label_font)
        draw.text((cx - (bbox2[2] - bbox2[0]) / 2, y + 36), label, font=label_font, fill=SOFT_WHITE)
    return img


def _scene_cta(w: int, h: int, t: float, beat: float, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    pulse = 0.5 + 0.5 * math.sin(beat * math.pi)
    _draw_mark(img, w // 2, int(h * 0.22), int(min(w, h) * 0.10), t * 10.0, pulse)
    draw = ImageDraw.Draw(img)
    _center_block(draw, campaign["close"], _font("serif", _scaled(26, w, h)), int(h * 0.40), CREAM, w)
    pill = [int(w * 0.12), int(h * 0.56), int(w * 0.88), int(h * 0.66)]
    draw.rounded_rectangle(pill, radius=min(32, (pill[3] - pill[1]) // 2), fill=GOLD)
    cta_font = _fit_text(campaign["primary_cta"], "sans_bold", 22, 14, int(w * 0.70), w, h)
    _center(draw, campaign["primary_cta"], cta_font, int(h * 0.585), INK, w)
    _center(
        draw,
        campaign["secondary_cta"].upper(),
        _fit_text(campaign["secondary_cta"].upper(), "sans", 14, 10, int(w * 0.90), w, h),
        int(h * 0.70),
        GOLD_LIGHT,
        w,
    )
    _center_block(draw, campaign["trust"], _font("sans_light", _scaled(13, w, h)), int(h * 0.78), SOFT_WHITE, w)
    return img


def render_frame(t: float, beats: list[float], size: tuple[int, int], campaign_name: str = "register") -> Image.Image:
    campaign = get_campaign(campaign_name)
    w, h = size
    if not beats:
        beats = [0.0, 0.75, 1.5]
    duration_end = beats[-1] + (beats[-1] - beats[-2] if len(beats) > 1 else 0.75)
    total = max(duration_end, 1.0)
    beat_idx = sum(1 for b in beats if b <= t)
    last_beat = beats[beat_idx - 1] if beat_idx else 0.0
    local_beat = beat_idx + (t - last_beat) / 0.75
    progress = min(1.0, t / total)

    if progress < 0.12:
        frame = _scene_logo(w, h, t, local_beat, campaign)
    elif progress < 0.26:
        frame = _scene_hook(w, h, campaign)
    elif progress < 0.42:
        frame = _scene_image(IMG_FANCY, campaign["image_caption"], campaign["image_sub"], w, h, t)
    elif progress < 0.56:
        frame = _scene_colors(w, h, local_beat)
    elif progress < 0.72:
        frame = _scene_image(IMG_RING, campaign["product_caption"], campaign["product_sub"], w, h, t)
    elif progress < 0.84:
        frame = _scene_trust(w, h, campaign)
    else:
        frame = _scene_cta(w, h, t, local_beat, campaign)

    _url_bar(frame, BRAND["url"])
    if beat_idx > 0 and beats:
        last = beats[min(beat_idx, len(beats)) - 1]
        dt = t - last
        if 0 <= dt < 0.10:
            flash = Image.new("RGBA", (w, h), (255, 255, 255, int(28 * (1 - dt / 0.10))))
            frame = Image.alpha_composite(frame, flash)
    return frame.convert("RGB")
