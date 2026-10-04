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


def _font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONTS[key], size)


def _scaled(base: int, w: int, h: int) -> int:
    return max(12, int(base * min(w, h) / 720))


def _cover(path: Path, size: tuple[int, int], zoom: float = 1.0, pan: float = 0.0) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    tw, th = size
    scale = max(tw / img.width, th / img.height) * zoom
    nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x = int((nw - tw) * (0.5 + pan * 0.18))
    y = int((nh - th) * 0.5)
    return img.crop((x, y, x + tw, y + th))


def _center(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill, width: int):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) / 2, y), text, font=font, fill=fill)


def _vignette(img: Image.Image, strength: float = 0.55) -> Image.Image:
    w, h = img.size
    overlay = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-int(w * 0.15), -int(h * 0.12), int(w * 1.15), int(h * 1.12)), fill=255)
    overlay = overlay.filter(ImageFilter.GaussianBlur(90))
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
    draw = ImageDraw.Draw(img, "RGBA")
    bar = Image.new("RGBA", (w, 42), (10, 10, 10, 170))
    img.alpha_composite(bar, (0, 0))
    draw = ImageDraw.Draw(img)
    _center(draw, url.upper(), _font("sans", _scaled(13, w, h)), 12, GOLD, w)


def _scene_logo(w: int, h: int, t: float, beat: float, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    pulse = 0.5 + 0.5 * math.sin(beat * math.pi)
    rot = t * 8.0
    _draw_mark(img, w // 2, int(h * 0.36), int(min(w, h) * 0.14), rot, pulse)
    draw = ImageDraw.Draw(img)
    _center(draw, "COLOUR DIAM", _font("serif", _scaled(48, w, h)), int(h * 0.58), GOLD_LIGHT, w)
    _center(draw, BRAND["since"].upper(), _font("sans_light", _scaled(16, w, h)), int(h * 0.65), GOLD, w)
    _center(draw, campaign["hook"], _font("serif_italic", _scaled(22, w, h)), int(h * 0.74), CREAM, w)
    return img


def _scene_hook(w: int, h: int, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    draw = ImageDraw.Draw(img)
    _center(draw, campaign["hook"].upper(), _font("sans_light", _scaled(14, w, h)), int(h * 0.34), GOLD, w)
    _center(draw, campaign["headline"], _font("serif", _scaled(34, w, h)), int(h * 0.42), CREAM, w)
    y = int(h * 0.56)
    draw.line((w * 0.28, y, w * 0.72, y), fill=GOLD, width=1)
    _center(draw, campaign["promise"], _font("sans_light", _scaled(15, w, h)), y + 22, SOFT_WHITE, w)
    return img


def _scene_image(path: Path, caption: str, sub: str, w: int, h: int, t: float) -> Image.Image:
    zoom = 1.08 + 0.06 * (t % 4) / 4.0
    pan = math.sin(t * 0.35)
    img = _cover(path, (w, h), zoom=zoom, pan=pan)
    img = _vignette(img, 0.62)
    draw = ImageDraw.Draw(img)
    _center(draw, caption, _font("serif", _scaled(32, w, h)), int(h * 0.76), CREAM, w)
    _center(draw, sub, _font("sans_light", _scaled(15, w, h)), int(h * 0.82), GOLD_LIGHT, w)
    return img


def _scene_colors(w: int, h: int, beat: float) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    draw = ImageDraw.Draw(img)
    _center(draw, "FANCY COLOUR DIAMONDS", _font("sans_light", _scaled(14, w, h)), int(h * 0.14), GOLD, w)
    _center(draw, "Nature's Rarest Palette", _font("serif", _scaled(30, w, h)), int(h * 0.19), CREAM, w)
    cols = 4
    gap = 16
    box = int((w - gap * (cols + 1)) / cols)
    top = int(h * 0.34)
    idx = int(beat) % len(DIAMOND_COLORS)
    for i, (name, color) in enumerate(DIAMOND_COLORS):
        r, c = i // cols, i % cols
        x = gap + c * (box + gap)
        y = top + r * (box + 48)
        rbox = [x, y, x + box, y + box]
        if i == idx:
            draw.rounded_rectangle(
                [x - 4, y - 4, x + box + 4, y + box + 4],
                radius=box // 2,
                outline=GOLD,
                width=2,
            )
        draw.ellipse(rbox, fill=color)
        label_font = _font("sans", _scaled(12, w, h))
        bbox = draw.textbbox((0, 0), name.upper(), font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text((x + (box - tw) / 2, y + box + 8), name.upper(), font=label_font, fill=GOLD_LIGHT if i == idx else SOFT_WHITE)
    return img


def _scene_trust(w: int, h: int, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    draw = ImageDraw.Draw(img)
    _center(draw, "WHY COLOUR DIAM", _font("sans_light", _scaled(14, w, h)), int(h * 0.22), GOLD, w)
    _center(draw, campaign["trust"], _font("serif", _scaled(26, w, h)), int(h * 0.32), CREAM, w)
    points = [
        ("GIA", "Certified stones"),
        ("1984", "Family legacy"),
        ("100%", "Money back"),
    ]
    y = int(h * 0.52)
    gap = w // 3
    for i, (year, label) in enumerate(points):
        cx = gap * i + gap // 2
        bbox = draw.textbbox((0, 0), year, font=_font("serif", _scaled(22, w, h)))
        draw.text((cx - (bbox[2] - bbox[0]) / 2, y), year, font=_font("serif", _scaled(22, w, h)), fill=GOLD)
        bbox2 = draw.textbbox((0, 0), label, font=_font("sans_light", _scaled(13, w, h)))
        draw.text((cx - (bbox2[2] - bbox2[0]) / 2, y + 36), label, font=_font("sans_light", _scaled(13, w, h)), fill=SOFT_WHITE)
    return img


def _scene_cta(w: int, h: int, t: float, beat: float, campaign: dict) -> Image.Image:
    img = Image.new("RGBA", (w, h), (*INK, 255))
    pulse = 0.5 + 0.5 * math.sin(beat * math.pi)
    _draw_mark(img, w // 2, int(h * 0.26), int(min(w, h) * 0.11), t * 10.0, pulse)
    draw = ImageDraw.Draw(img)
    _center(draw, campaign["close"], _font("serif", _scaled(26, w, h)), int(h * 0.46), CREAM, w)
    pill = [int(w * 0.16), int(h * 0.56), int(w * 0.84), int(h * 0.66)]
    draw.rounded_rectangle(pill, radius=32, fill=GOLD)
    _center(draw, campaign["primary_cta"], _font("sans_bold", _scaled(22, w, h)), int(h * 0.585), INK, w)
    _center(draw, campaign["secondary_cta"].upper(), _font("sans", _scaled(14, w, h)), int(h * 0.70), GOLD_LIGHT, w)
    _center(draw, campaign["trust"], _font("sans_light", _scaled(13, w, h)), int(h * 0.78), SOFT_WHITE, w)
    return img


def render_frame(t: float, beats: list[float], size: tuple[int, int], campaign_name: str = "register") -> Image.Image:
    campaign = get_campaign(campaign_name)
    w, h = size
    duration_end = beats[-1] + (beats[-1] - beats[-2] if len(beats) > 1 else 0.75)
    total = max(duration_end, 1.0)
    beat_idx = sum(1 for b in beats if b <= t)
    local_beat = beat_idx + (t - (beats[beat_idx - 1] if beat_idx else 0)) / 0.75
    progress = min(1.0, t / total)

    if progress < 0.12:
        frame = _scene_logo(w, h, t, local_beat, campaign)
    elif progress < 0.26:
        frame = _scene_hook(w, h, campaign)
    elif progress < 0.42:
        frame = _scene_image(IMG_FANCY, "Fancy Colour Diamonds", "Nature's rarest palette", w, h, t)
    elif progress < 0.56:
        frame = _scene_colors(w, h, local_beat)
    elif progress < 0.72:
        frame = _scene_image(IMG_RING, "Solitaire Elegance", "A sparkle that lasts forever", w, h, t)
    elif progress < 0.84:
        frame = _scene_trust(w, h, campaign)
    else:
        frame = _scene_cta(w, h, t, local_beat, campaign)

    _url_bar(frame, BRAND["url"])
    if beat_idx > 0 and beats:
        last = beats[min(beat_idx, len(beats) - 1) - 1] if beat_idx else 0
        dt = t - last
        if 0 <= dt < 0.10:
            flash = Image.new("RGBA", (w, h), (255, 255, 255, int(28 * (1 - dt / 0.10))))
            frame = Image.alpha_composite(frame, flash)
    return frame.convert("RGB")
