"""Render bottom-to-top labels used on the vertical IDEF0 arrows."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
OUT = HERE / "labels"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LABELS = {
    "control-permission": "Разрешения Android",
    "control-rules": "Правила контекста",
    "control-dwell": "Выдержка и дедупликация",
    "mechanism-app": "Приложение GoCue",
    "mechanism-geofence": "Геозоны Android",
    "mechanism-notification": "Уведомления Android",
    "mechanism-db": "Локальная база данных",
}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    font = ImageFont.truetype(FONT, 14)
    for name, label in LABELS.items():
        bounds = font.getbbox(label)
        width = bounds[2] - bounds[0] + 8
        height = bounds[3] - bounds[1] + 8
        image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.text((4 - bounds[0], 4 - bounds[1]), label, font=font, fill="#1E3349")
        image.rotate(90, expand=True).save(OUT / f"{name}.png")


if __name__ == "__main__":
    main()
