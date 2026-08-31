from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from kitchenwatch.settings import ROOT

OUT = ROOT / "fixtures" / "fridge_honest.jpg"


def render_fridge_honest(path: Path = OUT, *, as_of: date | None = None) -> Path:
    """Planted shelf card. Dates match Reset demo shelf (milk tomorrow)."""
    day = as_of or date.today()
    packs = (
        ("WHOLE MILK", "1 carton", f"EXP {(day + timedelta(days=1)).isoformat()}", (245, 245, 245), (20, 20, 20)),
        ("EGGS", "6 count", f"EXP {(day + timedelta(days=6)).isoformat()}", (250, 230, 140), (20, 20, 20)),
        ("BABY SPINACH", "200 g", f"EXP {(day + timedelta(days=2)).isoformat()}", (70, 130, 70), (250, 250, 250)),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1200, 800), (18, 22, 28))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("Helvetica.ttc", 36)
        pack_font = ImageFont.truetype("Helvetica.ttc", 40)
        small_font = ImageFont.truetype("Helvetica.ttc", 28)
    except OSError:
        title_font = ImageFont.load_default()
        pack_font = title_font
        small_font = title_font

    draw.text((40, 30), "KITCHENWATCH FIXTURE FRIDGE", fill=(220, 220, 220), font=title_font)
    draw.text((40, 80), "Do not invent items that are not on this shelf.", fill=(160, 160, 160), font=small_font)

    width = 340
    gap = 40
    left = 50
    top = 180
    for i, (name, qty, exp, fill, ink) in enumerate(packs):
        x = left + i * (width + gap)
        draw.rounded_rectangle((x, top, x + width, top + 420), radius=18, fill=fill)
        draw.text((x + 24, top + 40), name, fill=ink, font=pack_font)
        draw.text((x + 24, top + 160), qty, fill=ink, font=small_font)
        draw.text((x + 24, top + 240), exp, fill=ink, font=pack_font)

    image.save(path, "JPEG", quality=92)
    return path


if __name__ == "__main__":
    print(render_fridge_honest())
