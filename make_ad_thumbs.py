"""make_ad_thumbs.py: 16:9 Roblox ad creatives (1920x1080) for Everybody Has a Secret, built from sir's thumbnail.
Output: thumbnails/ads/ehas_ad_<n>.png"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

R = "./"
SRC = R + "thumbnails/sir/ehas_thumb_sir.jpg"
OUT = R + "thumbnails/ads/"
os.makedirs(OUT, exist_ok=True)
FONT = "C:/Windows/Fonts/impact.ttf"


def outlined(d, xy, text, size, fill, anchor="mm", stroke=10):
    f = ImageFont.truetype(FONT, size)
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))


def shade(im, top=True, h=330, alpha=190):
    g = Image.new("L", (1, h))
    for y in range(h):
        g.putpixel((0, y), int(alpha * (1 - y / h)) if top else int(alpha * y / h))
    g = g.resize((im.width, h))
    black = Image.new("RGB", (im.width, h), (0, 0, 0))
    box = (0, 0) if top else (0, im.height - h)
    im.paste(black, box, g)


base = Image.open(SRC).convert("RGB").resize((1920, 1080), Image.LANCZOS)

# 1) hook: steal it, don't get caught
a = base.copy()
shade(a, top=False, h=380)
d = ImageDraw.Draw(a)
outlined(d, (960, 850), "STEAL IT.", 150, (255, 215, 60))
outlined(d, (960, 985), "DON'T GET CAUGHT.", 110, (255, 255, 255))
a.save(OUT + "ehas_ad_1.png")

# 2) title card: the game's name, big and red-accented
b = base.copy()
shade(b, top=False, h=380)
d = ImageDraw.Draw(b)
outlined(d, (960, 865), "EVERYBODY HAS", 130, (255, 255, 255))
outlined(d, (960, 990), "A SECRET", 150, (255, 70, 70))
b.save(OUT + "ehas_ad_2.png")

# 3) question hook + emoji-free arrow pointing at the thief
c = base.copy()
shade(c, top=True, h=300)
d = ImageDraw.Draw(c)
outlined(d, (960, 110), "WHAT'S YOUR SECRET?", 130, (255, 255, 255))
c.save(OUT + "ehas_ad_3.png")

# 4) social-deduction angle: one of them is lying
e = base.copy().filter(ImageFilter.GaussianBlur(0))
shade(e, top=True, h=300)
shade(e, top=False, h=260, alpha=170)
d = ImageDraw.Draw(e)
outlined(d, (960, 110), "ONE OF YOU IS THE THIEF", 112, (255, 255, 255))
outlined(d, (960, 990), "TRUST NO ONE", 120, (255, 215, 60))
e.save(OUT + "ehas_ad_4.png")

# contact sheet for review
sheet = Image.new("RGB", (1920, 1080), (20, 20, 20))
for i, p in enumerate(["ehas_ad_1.png", "ehas_ad_2.png", "ehas_ad_3.png", "ehas_ad_4.png"]):
    im = Image.open(OUT + p).resize((960, 540))
    sheet.paste(im, ((i % 2) * 960, (i // 2) * 540))
sheet.save(OUT + "sheet.png")
print("ok", sorted(os.listdir(OUT)))
