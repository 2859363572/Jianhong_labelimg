from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "img" / "labelimg.ico"
SIZE = 256


def rounded_line(draw, points, fill, width):
    draw.line(points, fill=fill, width=width, joint="curve")
    radius = width // 2
    for x, y in (points[0], points[-1]):
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)


def create_icon():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((12, 12, 244, 244), radius=52, fill="#181C22", outline="#303741", width=8)
    draw.polygon(((28, 178), (74, 126), (111, 164), (153, 106), (228, 179), (228, 218), (28, 218)), fill="#303C49")
    draw.polygon(((28, 190), (84, 158), (131, 204), (181, 168), (228, 197), (228, 218), (28, 218)), fill="#222A33")

    blue = "#1597F5"
    mint = "#28D7B0"
    corner_width = 13
    rounded_line(draw, ((55, 84), (55, 55), (84, 55)), blue, corner_width)
    rounded_line(draw, ((172, 55), (201, 55), (201, 84)), blue, corner_width)
    rounded_line(draw, ((55, 172), (55, 201), (84, 201)), blue, corner_width)
    rounded_line(draw, ((172, 201), (201, 201), (201, 172)), blue, corner_width)

    box = (84, 91, 172, 174)
    draw.rectangle(box, outline=mint, width=8)
    for x, y in ((84, 91), (172, 91), (84, 174), (172, 174)):
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), fill=mint)

    image.save(OUTPUT, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    create_icon()
    print(OUTPUT)
