"""Secret-free Pillow compatibility checks for the Colour Diam renderer."""

from pathlib import Path
from tempfile import TemporaryDirectory

import PIL
from PIL import Image, ImageDraw

from generator import render
from generator.campaigns import get_campaign


def _version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split(".") if part.isdigit())


def _assert_frame(image: Image.Image, size: tuple[int, int]) -> None:
    assert image.size == size
    assert image.mode in {"RGB", "RGBA"}
    extrema = image.convert("RGB").getextrema()
    assert any(low != high for low, high in extrema), "Rendered frame is unexpectedly flat"


def main() -> None:
    assert _version_tuple(PIL.__version__) >= (13, 0, 0), PIL.__version__

    size = (320, 180)
    campaign = get_campaign("register")

    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        source = tmp / "synthetic-source.png"
        synthetic = Image.new("RGBA", (96, 64), (18, 24, 36, 255))
        draw = ImageDraw.Draw(synthetic)
        draw.rectangle((8, 8, 52, 44), fill=(232, 160, 184, 210))
        draw.ellipse((42, 12, 88, 58), fill=(232, 197, 71, 180))
        synthetic.save(source)

        covered = render._cover(source, size, zoom=1.05, pan=0.2)
        _assert_frame(covered, size)
        _assert_frame(render._vignette(covered), size)
        _assert_frame(render._scene_image(source, "Synthetic fixture", "Not published", *size, 1.25), size)

        scenes = [
            render._scene_logo(*size, 0.25, 0.5, campaign),
            render._scene_hook(*size, campaign),
            render._scene_colors(*size, 1.0),
            render._scene_trust(*size, campaign),
            render._scene_cta(*size, 2.0, 1.0, campaign),
            render.render_frame(0.0, [0.5, 1.0, 1.5, 2.0], size, "register"),
            render.render_frame(2.4, [0.5, 1.0, 1.5, 2.0], size, "register"),
        ]

        for index, frame in enumerate(scenes):
            _assert_frame(frame, size)
            png = tmp / f"frame-{index}.png"
            jpg = tmp / f"frame-{index}.jpg"
            frame.save(png)
            frame.convert("RGB").save(jpg, quality=90)
            with Image.open(png) as reopened_png:
                reopened_png.load()
                assert reopened_png.size == size
            with Image.open(jpg) as reopened_jpg:
                reopened_jpg.load()
                assert reopened_jpg.size == size

    print(f"Pillow {PIL.__version__} passed synthetic renderer compatibility checks")


if __name__ == "__main__":
    main()
