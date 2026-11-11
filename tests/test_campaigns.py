"""Campaign, copy, and brand sanity checks for Colour Diam conversion."""

from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
generator_package = types.ModuleType("generator")
generator_package.__path__ = [str(ROOT / "generator")]
sys.modules["generator"] = generator_package

from generator.brand import BRAND, FORMATS, FONTS
from generator.campaigns import CAMPAIGNS, get_campaign
from generator.copy import pack_for


REQUIRED_KEYS = {
    "goal",
    "primary_cta",
    "secondary_cta",
    "url",
    "hook",
    "headline",
    "promise",
    "trust",
    "close",
    "image_caption",
    "image_sub",
    "product_caption",
    "product_sub",
    "caption",
    "hashtags",
}


def main() -> None:
    assert set(CAMPAIGNS) == {"register", "shop", "enquire"}
    assert set(FORMATS) == {"vertical", "horizontal", "square"}
    assert BRAND["url"] == "www.colourdiam.com"
    assert BRAND["phone"] == "+852 96440155"

    for name, data in CAMPAIGNS.items():
        missing = REQUIRED_KEYS - set(data)
        assert not missing, f"{name} missing {missing}"
        assert "www.colourdiam.com" in data["secondary_cta"]
        assert data["url"].startswith("https://www.colourdiam.com/")
        pack = pack_for(name)
        assert pack["cta"] == data["primary_cta"]
        assert pack["url"] == data["url"]
        assert pack["titles"]
        assert "www.colourdiam.com" in pack["description"] or "colourdiam.com" in pack["description"]

    assert get_campaign("register")["primary_cta"] == "REGISTER NOW"
    try:
        get_campaign("unknown")
        raise AssertionError("unknown campaign should fail")
    except ValueError:
        pass

    for path in FONTS.values():
        assert Path(path).is_file(), path

    print("Campaign, copy, and brand checks passed")


if __name__ == "__main__":
    main()
