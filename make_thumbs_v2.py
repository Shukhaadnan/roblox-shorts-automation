"""Petnap! Steal a Pet - store thumbnails v2 (1920x1080) + icon (512).
Source stills: videos/land_sap_take8.mp4 (staged close-ups from steal_a_pet/demo/ThumbPilot).
Run with ./tts/.venv/Scripts/python.exe tools/make_thumbs_v2.py
"""
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = "./"
SRC = ROOT + "/videos/land_sap_take8.mp4"
OUT = ROOT + "/thumbnails/v2"
TMP = "./tmp/tsrc"
IMPACT = "C:/Windows/Fonts/impact.ttf"
BLACK = "C:/Windows/Fonts/ariblk.ttf"
os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)


def frame(t, src=SRC):
    p = f"{TMP}/v2_{os.path.basename(src)}_{t}.png"
    if not os.path.exists(p):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", src, "-frames:v", "1",
                        "-vf", "crop=1690:725:0:205", p], check=True)
    return Image.open(p).convert("RGB")


def grade(im, sat=1.35, con=1.12, bri=1.04, sharp=True):
    im = ImageEnhance.Color(im).enhance(sat)
    im = ImageEnhance.Contrast(im).enhance(con)
    im = ImageEnhance.Brightness(im).enhance(bri)
    if sharp:
        im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=90, threshold=2))
    return im


def fit(im, box, size):
    """crop box (x0,y0,x1,y1) then resize to size with lanczos"""
    return im.crop(box).resize(size, Image.LANCZOS)


def radial(size, cx, cy, r, color, strength=1.0):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    lay = np.zeros((h, w, 4), np.uint8)
    lay[..., 0], lay[..., 1], lay[..., 2] = color
    lay[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(lay, "RGBA")


def add_glow(im, cx, cy, r, color, strength=0.6):
    """additive light bloom"""
    base = np.asarray(im).astype(np.float32)
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    a = (np.clip(1 - d, 0, 1) ** 2 * strength)[..., None]
    base = base + a * np.array(color, np.float32)[None, None, :]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def vignette(im, amt=0.45):
    w, h = im.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / math.sqrt(2)
    f = 1 - amt * np.clip((d - 0.45) / 0.55, 0, 1) ** 1.6
    a = np.asarray(im).astype(np.float32) * f[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def speed_lines(im, cx, cy, n=70, inner=0.55, color=(255, 255, 255), alpha=110, seed=3):
    rng = np.random.default_rng(seed)
    w, h = im.size
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    R = math.hypot(w, h)
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r0 = R * rng.uniform(inner, inner + 0.12)
        wid = rng.uniform(0.004, 0.012)
        p1 = (cx + math.cos(a - wid) * R, cy + math.sin(a - wid) * R)
        p2 = (cx + math.cos(a + wid) * R, cy + math.sin(a + wid) * R)
        p0 = (cx + math.cos(a) * r0, cy + math.sin(a) * r0)
        d.polygon([p0, p1, p2], fill=color + (int(alpha * rng.uniform(0.5, 1)),))
    lay = lay.filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


def text_img(txt, font_path, size, fill_top, fill_bot, stroke=None, stroke_col=(0, 0, 0), inner=None):
    """big outlined text with vertical gradient fill + thick black outline + drop shadow; returns RGBA"""
    font = ImageFont.truetype(font_path, size)
    stroke = stroke if stroke is not None else max(6, size // 9)
    l, t, r, b = font.getbbox(txt, stroke_width=stroke)
    W, H = r - l + 40, b - t + 50
    off = (20 - l, 20 - t)
    # shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).text((off[0] + 10, off[1] + 14), txt, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    # outline
    ol = Image.new("L", (W, H), 0)
    ImageDraw.Draw(ol).text(off, txt, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    # fill mask
    fm = Image.new("L", (W, H), 0)
    ImageDraw.Draw(fm).text(off, txt, font=font, fill=255)
    grad = np.zeros((H, W, 3), np.float32)
    k = np.linspace(0, 1, H)[:, None]
    grad[...] = (np.array(fill_top) * (1 - k) + np.array(fill_bot) * k)[:, None, :] if False else \
        (np.array(fill_top)[None, None, :] * (1 - k[..., None]) + np.array(fill_bot)[None, None, :] * k[..., None])
    gimg = Image.fromarray(grad.astype(np.uint8))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste((0, 0, 0, 170), (0, 0), sh)
    out.paste(stroke_col + (255,), (0, 0), ol)
    if inner:  # thin coloured inner ring between outline and fill
        im2 = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im2).text(off, txt, font=font, fill=255, stroke_width=max(2, stroke // 3), stroke_fill=255)
        out.paste(inner + (255,), (0, 0), im2)
    out.paste(gimg, (0, 0), fm)
    # glossy highlight on the top half of the letters
    hl = Image.new("L", (W, H), 0)
    hm = np.zeros((H, W), np.uint8)
    hm[: int(off[1] + (b - t) * 0.42), :] = 70
    hl = Image.fromarray(hm)
    hl = Image.composite(hl, Image.new("L", (W, H), 0), fm)
    out.paste((255, 255, 255, 255), (0, 0), hl)
    return out


def paste_rot(base, layer, center, angle=0):
    if angle:
        layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    x = int(center[0] - layer.width / 2)
    y = int(center[1] - layer.height / 2)
    out = base.convert("RGBA")
    _paste_neg(out, layer, x, y)
    return out.convert("RGB")


def _paste_neg(out, layer, x, y):
    # alpha_composite can't take negative offsets: crop the layer
    cx, cy = max(0, -x), max(0, -y)
    layer = layer.crop((cx, cy, layer.width, layer.height))
    out.alpha_composite(layer, (max(0, x), max(0, y)))
    return out


def arrow(base, tail, head, width=46, color=(255, 40, 40)):
    """chunky cartoon arrow with black outline"""
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    tx, ty = tail
    hx, hy = head
    ang = math.atan2(hy - ty, hx - tx)
    L = math.hypot(hx - tx, hy - ty)
    hl = width * 2.0
    ux, uy = math.cos(ang), math.sin(ang)
    px, py = -uy, ux
    bx, by = hx - ux * hl, hy - uy * hl
    pts = [(tx + px * width / 2, ty + py * width / 2), (bx + px * width / 2, by + py * width / 2),
           (bx + px * width * 1.25, by + py * width * 1.25), (hx, hy),
           (bx - px * width * 1.25, by - py * width * 1.25), (bx - px * width / 2, by - py * width / 2),
           (tx - px * width / 2, ty - py * width / 2)]
    sh = [(x + 8, y + 10) for x, y in pts]
    d.polygon(sh, fill=(0, 0, 0, 120))
    lay = lay.filter(ImageFilter.GaussianBlur(5))
    d = ImageDraw.Draw(lay)
    d.polygon(pts, fill=color + (255,), outline=(0, 0, 0, 255))
    d.line(pts + [pts[0]], fill=(0, 0, 0, 255), width=10, joint="curve")
    out = base.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


def badge(base, txt, center, size, bg=(255, 40, 140), fg=(255, 255, 255), angle=-6, font=BLACK):
    font_o = ImageFont.truetype(font, size)
    l, t, r, b = font_o.getbbox(txt)
    pad = size // 3
    W, H = r - l + pad * 2 + 20, b - t + pad * 2 + 20
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((10, 10, W - 10, H - 10), radius=H // 3, fill=bg + (255,), outline=(0, 0, 0, 255), width=max(6, size // 10))
    d.text((10 + pad - l, 10 + pad - t), txt, font=font_o, fill=fg, stroke_width=max(3, size // 16), stroke_fill=(0, 0, 0))
    return paste_rot(base, lay, center, angle)


def sparkles(base, pts, color=(255, 240, 200)):
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for (x, y, s) in pts:
        d.polygon([(x, y - s), (x + s * 0.22, y - s * 0.22), (x + s, y), (x + s * 0.22, y + s * 0.22), (x, y + s),
                   (x - s * 0.22, y + s * 0.22), (x - s, y), (x - s * 0.22, y - s * 0.22)], fill=color + (255,))
    glow = lay.filter(ImageFilter.GaussianBlur(8))
    out = base.convert("RGBA")
    out.alpha_composite(glow)
    out.alpha_composite(lay)
    return out.convert("RGB")


SZ = (1920, 1080)


# ---------------------------------------------------------------- A: STEAL IT! (reach for the SECRET pet)
def thumb_grab():
    im = frame(11.5)
    # 16:9 crop: drop the Roblox buttons (x<170) and the in-game label (top), zoom on hand + cat
    box = (330, 70, 330 + 1162, 70 + 654)
    im = fit(im, box, SZ)
    im = grade(im, 1.4, 1.14, 1.05)
    im = add_glow(im, 1330, 560, 620, (150, 60, 255), 0.55)   # purple aura around the SECRET pet
    im = add_glow(im, 1180, 140, 300, (0, 230, 255), 0.35)
    im = add_glow(im, 860, 500, 260, (255, 255, 255), 0.18)   # the hand / contact point
    im = vignette(im, 0.5)
    im = sparkles(im, [(1630, 220, 34), (1000, 210, 26), (1760, 640, 22), (1540, 900, 26), (1090, 830, 18)])
    t1 = text_img("STEAL IT!", IMPACT, 290, (255, 250, 120), (255, 150, 0), stroke=26)
    im = paste_rot(im, t1, (520, 200), 5)
    im = badge(im, "SECRET", (1500, 95), 90, bg=(255, 30, 120), angle=-5)
    im = arrow(im, (1790, 980), (1560, 760), width=56, color=(255, 40, 40))
    return im


# ---------------------------------------------------------------- B: RUN!! (carry the SECRET pet, rivals chase)
def thumb_run():
    im = frame(28.6)
    box = (400, 0, 1690, 725)
    im = fit(im, box, SZ)
    im = grade(im, 1.35, 1.15, 1.05)
    im = add_glow(im, 590, 330, 480, (140, 60, 255), 0.6)
    im = add_glow(im, 640, 120, 220, (0, 220, 255), 0.3)
    im = speed_lines(im, 600, 500, n=90, inner=0.40, alpha=85)
    im = vignette(im, 0.45)
    t1 = text_img("RUN!!", IMPACT, 340, (255, 95, 80), (205, 0, 0), stroke=26)
    im = paste_rot(im, t1, (1530, 300), -8)
    im = badge(im, "SECRET PET", (1520, 610), 84, bg=(255, 30, 120), angle=-6)
    im = sparkles(im, [(330, 160, 28), (930, 120, 24), (930, 560, 20), (300, 520, 22)])
    return im


# ---------------------------------------------------------------- C: laser door (locked out, pet so close)
def thumb_laser():
    im = frame(17.5)
    box = (560, 30, 560 + 1130, 30 + 636)
    im = fit(im, box, SZ)
    im = grade(im, 1.35, 1.15, 1.03)
    im = add_glow(im, 980, 470, 900, (255, 30, 30), 0.25)
    im = vignette(im, 0.45)
    t1 = text_img("LOCKED OUT!", IMPACT, 220, (255, 255, 255), (255, 215, 60), stroke=22)
    im = paste_rot(im, t1, (1250, 940), -3)
    im = badge(im, "SECRET", (330, 120), 84, bg=(255, 30, 120), angle=-6)
    return im


def icon_from(t, box, words=None, wsize=150, wpos=(256, 440), glow=(256, 170)):
    im = frame(t)
    im = fit(im, box, (1024, 1024))
    im = grade(im, 1.4, 1.15, 1.05)
    im = add_glow(im, glow[0] * 2, glow[1] * 2, 560, (150, 60, 255), 0.55)
    im = vignette(im, 0.55)
    if words:
        t1 = text_img(words, IMPACT, wsize * 2, (255, 250, 120), (255, 150, 0), stroke=wsize // 5)
        im = paste_rot(im, t1, (wpos[0] * 2, wpos[1] * 2), 4)
    return im.resize((512, 512), Image.LANCZOS)


def main():
    outs = {}
    outs["steal_a_pet_thumb"] = thumb_grab()
    outs["steal_a_pet_thumb2"] = thumb_run()
    outs["steal_a_pet_thumb3"] = thumb_laser()
    for k, v in outs.items():
        v.save(f"{OUT}/{k}.png")
    # icon: the thief with the SECRET pet over his head, rivals right behind him
    icon = icon_from(11.5, (430, 40, 430 + 685, 725), "STEAL!", 118, (256, 455), glow=(330, 190))
    icon.save(f"{OUT}/steal_a_pet_icon.png")
    icon_b = icon_from(28.6, (530, 10, 530 + 680, 690), None, glow=(220, 150))
    icon_b.save(f"{OUT}/steal_a_pet_icon_b.png")
    # contact sheet + small-size previews
    sheet = Image.new("RGB", (1920 + 40, 1080 + 60), (30, 30, 40))
    small = [outs[k].resize((640, 360), Image.LANCZOS) for k in outs]
    for i, s in enumerate(small):
        sheet.paste(s, (10 + i * 650, 10))
    sheet.paste(icon.resize((360, 360)), (10, 400))
    sheet.paste(icon_b.resize((360, 360)), (380, 400))
    sheet.paste(icon.resize((150, 150)), (760, 400))
    for i, k in enumerate(outs):
        sheet.paste(outs[k].resize((384, 216), Image.LANCZOS), (930 + (i % 2) * 400, 400 + (i // 2) * 230))
    sheet = sheet.crop((0, 0, 1960, 870))
    sheet.save(f"{OUT}/sheet.png")
    print("ok", list(outs))


if __name__ == "__main__":
    main()
