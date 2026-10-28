"""Render the IDEF0 A-0 diagram with one arrow per flow.

PlantUML's automatic layout cannot keep twelve ICOM arrows and their
labels aligned reliably. The .puml file remains the editable structural
source; this script makes the publication SVG/PNG with fixed geometry.
"""

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
OUT = HERE / "rendered"
WIDTH, HEIGHT, SCALE = 1200, 920, 2
BOX = (410, 320, 790, 600)
INK = "#1E3349"
LINE = "#34536F"
BLUE = "#2D70B2"
FONT_FILE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

INPUTS = [
    (380, "Намерения пользователя"),
    (460, "Настройки мест"),
    (540, "События геозон ENTER / EXIT"),
]
CONTROLS = [
    (490, "Разрешения Android"),
    (600, "Правила контекста"),
    (710, "Выдержка и дедупликация"),
]
OUTPUTS = [
    (380, "Список подходящих дел"),
    (460, "Групповое уведомление"),
    (540, "Запись в журнале событий"),
]
MECHANISMS = [
    (455, "Приложение GoCue"),
    (550, "Геозоны Android"),
    (650, "Уведомления Android"),
    (745, "Локальная база данных"),
]


def svg() -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#34536F"/></marker></defs>',
        '<rect width="1200" height="920" fill="white"/>',
        '<text x="600" y="38" text-anchor="middle" font-family="DejaVu Sans" font-size="25" font-weight="bold" fill="#1E3349">Контекстная диаграмма IDEF0 · A-0</text>',
        f'<rect x="{BOX[0]}" y="{BOX[1]}" width="{BOX[2]-BOX[0]}" height="{BOX[3]-BOX[1]}" rx="0" fill="#EDF5FC" stroke="{BLUE}" stroke-width="2.5"/>',
        f'<text x="435" y="420" font-family="DejaVu Sans" font-size="27" fill="{INK}">Возвращать намерения</text>',
        f'<text x="435" y="458" font-family="DejaVu Sans" font-size="27" fill="{INK}">в подходящем месте</text>',
        f'<text x="758" y="577" font-family="DejaVu Sans" font-size="24" fill="{INK}">0</text>',
    ]

    def arrow(x1: int, y1: int, x2: int, y2: int) -> None:
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{LINE}" stroke-width="2.2" marker-end="url(#arrow)"/>')

    def horizontal(x: int, y: int, label: str) -> None:
        parts.append(f'<text x="{x}" y="{y-13}" font-family="DejaVu Sans" font-size="18" fill="{INK}">{escape(label)}</text>')

    def vertical(x: int, baseline: int, label: str) -> None:
        parts.append(f'<text transform="translate({x-15} {baseline}) rotate(-90)" font-family="DejaVu Sans" font-size="18" fill="{INK}">{escape(label)}</text>')

    for y, label in INPUTS:
        arrow(35, y, BOX[0], y)
        horizontal(37, y, label)
    for x, label in CONTROLS:
        arrow(x, 75, x, BOX[1])
        vertical(x, 307, label)
    for y, label in OUTPUTS:
        arrow(BOX[2], y, 1165, y)
        horizontal(815, y, label)
    for x, label in MECHANISMS:
        arrow(x, 890, x, BOX[3])
        vertical(x, 876, label)
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def png() -> Image.Image:
    s = SCALE
    image = Image.new("RGB", (WIDTH * s, HEIGHT * s), "white")
    draw = ImageDraw.Draw(image)
    regular = ImageFont.truetype(FONT_FILE, 18 * s)
    function = ImageFont.truetype(FONT_FILE, 27 * s)
    number = ImageFont.truetype(FONT_FILE, 24 * s)
    title = ImageFont.truetype(FONT_FILE, 25 * s)

    def xy(point: tuple[int, int]) -> tuple[int, int]:
        return (point[0] * s, point[1] * s)

    def arrow(start: tuple[int, int], end: tuple[int, int]) -> None:
        draw.line((xy(start), xy(end)), fill=LINE, width=2 * s)
        x, y = end
        if start[0] < x:
            tips = [(x, y), (x-12, y-6), (x-12, y+6)]
        elif start[1] < y:
            tips = [(x, y), (x-6, y-12), (x+6, y-12)]
        else:
            tips = [(x, y), (x-6, y+12), (x+6, y+12)]
        draw.polygon([xy(p) for p in tips], fill=LINE)

    def vertical(x: int, baseline: int, label: str) -> None:
        bounds = regular.getbbox(label)
        w, h = bounds[2] - bounds[0] + 4*s, bounds[3] - bounds[1] + 4*s
        text = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        ImageDraw.Draw(text).text((2*s-bounds[0], 2*s-bounds[1]), label, font=regular, fill=INK)
        turned = text.rotate(90, expand=True)
        image.paste(turned, ((x-33)*s, baseline*s-turned.height), turned)

    title_width = draw.textlength("Контекстная диаграмма IDEF0 · A-0", font=title)
    draw.text(((WIDTH*s-title_width)/2, 12*s), "Контекстная диаграмма IDEF0 · A-0", font=title, fill=INK)
    draw.rectangle((xy((BOX[0], BOX[1])), xy((BOX[2], BOX[3]))), fill="#EDF5FC", outline=BLUE, width=3*s)
    draw.text(xy((435, 385)), "Возвращать намерения", font=function, fill=INK)
    draw.text(xy((435, 423)), "в подходящем месте", font=function, fill=INK)
    draw.text(xy((758, 548)), "0", font=number, fill=INK)

    for y, label in INPUTS:
        arrow((35, y), (BOX[0], y))
        draw.text(xy((37, y-39)), label, font=regular, fill=INK)
    for x, label in CONTROLS:
        arrow((x, 75), (x, BOX[1]))
        vertical(x, 307, label)
    for y, label in OUTPUTS:
        arrow((BOX[2], y), (1165, y))
        draw.text(xy((815, y-39)), label, font=regular, fill=INK)
    for x, label in MECHANISMS:
        arrow((x, 890), (x, BOX[3]))
        vertical(x, 876, label)
    return image


def main() -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "01-context.svg").write_text(svg(), encoding="utf-8")
    png().save(OUT / "01-context.png")


if __name__ == "__main__":
    main()
