from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
VENDOR = ROOT / "vendor"

GOLD = (194, 153, 88)
GOLD_LIGHT = (232, 213, 176)
CREAM = (245, 234, 214)
INK = (10, 10, 10)
CHARCOAL = (22, 18, 16)
WHITE = (255, 255, 255)
SOFT_WHITE = (236, 232, 224)

DIAMOND_COLORS = [
    ("Pink", (232, 160, 184)),
    ("Yellow", (232, 197, 71)),
    ("Blue", (74, 126, 200)),
    ("Green", (124, 184, 138)),
    ("Orange", (232, 160, 90)),
    ("Purple", (155, 123, 184)),
    ("White", (232, 232, 232)),
    ("Brown", (166, 124, 90)),
]


def _first_font(*candidates: str) -> str:
    for path in candidates:
        if Path(path).is_file():
            return path
    return candidates[-1]


FONTS = {
    "serif": _first_font(
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ),
    "serif_bold": _first_font(
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ),
    "serif_italic": _first_font(
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ),
    "sans": _first_font(
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    "sans_light": _first_font(
        "/usr/share/fonts/truetype/lato/Lato-Light.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ),
    "sans_bold": _first_font(
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
}

LOGO_MARK = ASSETS / "products" / "ColorDiam.png"
LOGO_WORD = ASSETS / "logo" / "logo.png"
IMG_FANCY = ASSETS / "products" / "about71.png"
IMG_RING = ASSETS / "products" / "about66.png"

BRAND = {
    "name": "Colour Diam",
    "url": "www.colourdiam.com",
    "register": "www.colourdiam.com/register",
    "shop": "www.colourdiam.com/product",
    "enquire": "www.colourdiam.com/contactus",
    "phone": "+852 96440155",
    "tagline": "Elegant & Timeless Diamond Jewelry",
    "promise": "Certified Diamonds  |  Custom Designs  |  Exclusive Offers",
    "since": "Since 1984",
    "cta": "Shop Now & Shine Bright",
}

FORMATS = {
    "vertical": {"width": 720, "height": 1280, "label": "9:16 Reels / Shorts / TikTok"},
    "horizontal": {"width": 1280, "height": 720, "label": "16:9 YouTube"},
    "square": {"width": 1080, "height": 1080, "label": "1:1 Feed"},
}

FPS = 24
TEMPO_BPM = 80
BARS = 8
BEATS_PER_BAR = 4
