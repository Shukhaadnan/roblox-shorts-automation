"""reel_copy.py - re-creates sir's reference reel edit (DeKMjCAxIwo, "KnifeSwap") 1:1 in style, on Everybody Has a Secret.
Measured from the reference (refs/k): full-bleed 9:16 gameplay, ONE word on screen at a time (Montserrat ExtraBold,
white + soft dark glow, centre y = 59 %), key word in red, meme picture popup bottom-right, big countdown numerals,
icon stickers for the CTA, vertical whip-slide transitions (~0.1 s), the reel's own music/SFX bed ~6.7 dB under the
voice, cloned reference voice sped up (clone:ref1:fast), CTA "before I tell you the game name..." then the name.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, r"./tts")
import tts_words

V = "./videos/"
# Every new video = a new spec in tools/reels/<name>.json (different words/category, SAME edit). Usage:
#   <tts venv python> reel_copy.py tools/reels/<name>.json
SPEC = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "reels", "ehas_thief.json"), encoding="utf-8"))
RAW = SPEC["raw"]
BED = SPEC.get("bed", "./tts/clone/work/sep/htdemucs_ft/ref1_full/no_vocals.wav")
WORK = V + "reelcopy/" + SPEC["name"] + "/"
os.makedirs(WORK, exist_ok=True)
OUT = SPEC.get("out", V + "nocard/" + SPEC["name"] + ".mp4")
W, H, FPS = 1080, 1920, 30
CROP = SPEC.get("crop", "transpose=1,crop=821:1460:129:300") + ",scale=1080:1920:flags=lanczos," + SPEC.get("style", {}).get("grade", "eq=saturation=1.08")
# extra sources: {"key": {"path": ..., "crop": "<ffmpeg crop chain>"}}; a shot's 4th element picks one
RAWS = {"main": (RAW, CROP)}
for k, r in SPEC.get("raws", {}).items():
    RAWS[k] = (r["path"], r.get("crop", "transpose=1,crop=821:1460:129:300") + ",scale=1080:1920:flags=lanczos,eq=saturation=1.08")
FONT = V + "fonts/Montserrat-ExtraBold.ttf"
FONTB = V + "fonts/Montserrat-Black.ttf"

SCRIPT = SPEC["script"]
# ---- per-video STYLE (Oct 8: sir wants every reel to look/sound different -> no duplicate-template shadowban)
ST = SPEC.get("style", {})
FONTC = ST.get("font", FONT)                      # caption font
CAP_SIZE = ST.get("size", 92)
CAP_Y = ST.get("cap_y", 1133)
CAP_FILL = tuple(ST.get("color", [255, 255, 255])) + (255,)
ACCENT = tuple(ST.get("accent", [236, 52, 46])) + (255,)
CAP_BOX = ST.get("box")                           # None | [r,g,b] -> rounded box behind each word (CapCut look)
CAP_UPPER = ST.get("upper", False)
TRANS = ST.get("trans", "whip")                    # whip | flash | zoom | slide | cut
KB = ST.get("kb", 0.0)                             # slow ken-burns push-in per shot (0.05 = 5 %)
TITLE_Y = ST.get("title_y", 860)
RED = set(w.lower() for w in SPEC.get("red", []))           # key words shown in red (like "serial" in the reference)
SHOTS = [tuple(x) for x in SPEC["shots"]]                    # [first word index, raw source time, whip-in?]
POPUP = tuple(SPEC["popup"]["words"]) if SPEC.get("popup") else None   # picture popup bottom-right
COUNT = {int(k): v for k, v in SPEC.get("count", {}).items()}           # big numerals on word index
STICK = {int(k): v for k, v in SPEC.get("stick", {}).items()}           # bookmark / follow icons on word index
STICK_DUR = ST.get("stick_dur", 1.25)
STICK_Y = ST.get("stick_y", 900)
# ---- Oct 11 additions (ref4 "Ball Clash" copy); all optional, old specs unchanged:
#   "emoji": {word idx: {"e": "🍒", "dur": 0.65, "size": 480, "x": 540, "y": 900}}  colour emoji sticker pop-up
#   "end_card": {"image": <png/jpg>, "word": idx, "name": ["LINE1","LINE2"], "sub": "...", "w": 600, "y": 900,
#                "name_color": [r,g,b], "hide_caps": true}   game ICON CARD popping in at the end (swap image = 1 line)
#   shot transitions: "hwhip" (sideways smear), "wflash" (white flash), "rzoom" (radial zoom blur, also on shot 0)
#   shot source "CARD" (4th element): blurred gameplay + the end-card image + PLAY button tapped (game-page hook)
EMOJI = {int(k): v for k, v in SPEC.get("emoji", {}).items()}
CAP_Y_KEY = ST.get("cap_y_key", {})   # {"shop": 1640}: per-source caption height
ECARD = SPEC.get("end_card")

# ---------------------------------------------------------------- voice
vo = WORK + "vo.wav"
wj = WORK + "vo_words.json"
if os.path.exists(wj) and json.load(open(wj))["text"] == SCRIPT:
    words = json.load(open(wj))["words"]
else:
    words = tts_words.synth(SCRIPT, vo, "clone:ref1:fast", 1.18)
    json.dump({"text": SCRIPT, "words": words}, open(wj, "w"))
words = [list(w) for w in words]
_dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vo],
                            capture_output=True, text=True).stdout)
if tts_words._degenerate(words, _dur):  # broken whisper timings -> re-align the take (Oct 8)
    print("re-aligning word timings")
    words = [list(w) for w in tts_words.align_file(vo, SCRIPT)]
    json.dump({"text": SCRIPT, "words": words}, open(wj, "w"))
    print("degenerate after realign:", tts_words._degenerate(words, _dur))
assert len(words) == len(SCRIPT.split()), (len(words), len(SCRIPT.split()))
dur_vo = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", vo],
                              capture_output=True, text=True).stdout)
TOTAL = dur_vo + SPEC.get("tail", 0.35)   # Oct 11: optional longer end-card hold
NF = int(TOTAL * FPS)
print("voice", round(dur_vo, 2), "s,", len(words), "words,", round(len(words) / dur_vo, 2), "w/s")

# ---------------------------------------------------------------- shots -> frames
def shot_start(i):
    return 0.0 if i == 0 else max(0.0, words[SHOTS[i][0]][0] - 0.04)

bounds = [(shot_start(i), shot_start(i + 1) if i + 1 < len(SHOTS) else TOTAL) for i in range(len(SHOTS))]

def read_shot(src, dur, key="main"):
    n = int(round(dur * FPS)) + 2
    raw, crop = RAWS[key]
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{src:.3f}", "-i", raw, "-t", f"{dur + 0.2:.3f}",
                        "-vf", f"{crop},fps={FPS}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, np.uint8)
    fr = a[: (len(a) // (W * H * 3)) * W * H * 3].reshape(-1, H, W, 3)
    if len(fr) < n:
        fr = np.concatenate([fr, np.repeat(fr[-1:], n - len(fr), 0)])
    return fr

# ---------------------------------------------------------------- overlays
fcache = {}
def font(path, size):
    k = (path, size)
    if k not in fcache:
        fcache[k] = ImageFont.truetype(path, size)
    return fcache[k]

def glow_text(text, size, fill, fpath=FONT, glow=(0, 0, 0), ga=210, rad=9):
    f = font(fpath, size)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = rad * 3
    im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    sh = Image.new("L", im.size, 0)
    ImageDraw.Draw(sh).text((pad - bb[0], pad - bb[1]), text, font=f, fill=255,
                            stroke_width=max(2, size // 22), stroke_fill=255)
    sh = sh.filter(ImageFilter.GaussianBlur(rad))
    g = Image.new("RGBA", im.size, glow + (0,))
    g.putalpha(sh.point(lambda v: min(255, int(v * ga / 255 * 1.6))))
    im = Image.alpha_composite(im, g)
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=fill)
    return im

cap_cache = {}
def caption(word):
    clean = word.strip(",.!?")
    if clean not in cap_cache:
        red = word.lower() in RED or clean.lower() in RED
        txt = clean.upper() if CAP_UPPER else clean
        fill = ACCENT if red else CAP_FILL
        if CAP_BOX:
            f = font(FONTC, CAP_SIZE)
            bb = f.getbbox(txt)
            pw, ph = 34, 22
            im = Image.new("RGBA", (bb[2] - bb[0] + pw * 2, bb[3] - bb[1] + ph * 2), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), 26,
                                fill=tuple(ACCENT[:3]) + (255,) if red else tuple(CAP_BOX) + (235,))
            d.text((pw - bb[0], ph - bb[1]), txt, font=f, fill=(255, 255, 255, 255) if red else CAP_FILL)
            cap_cache[clean] = im
        else:
            cap_cache[clean] = glow_text(txt, CAP_SIZE, fill, FONTC)
    return cap_cache[clean]

def icon(kind):
    s = 190
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "bookmark":
        d.ellipse((8, 8, s - 8, s - 8), fill=(255, 255, 255, 255))
        d.polygon([(62, 46), (128, 46), (128, 146), (95, 118), (62, 146)], fill=(20, 20, 24, 255))
    else:  # follow: red circle with +
        d.ellipse((8, 8, s - 8, s - 8), fill=(254, 44, 85, 255))
        d.rectangle((86, 50, 104, 140), fill="white")
        d.rectangle((50, 86, 140, 104), fill="white")
    sh = im.split()[3].filter(ImageFilter.GaussianBlur(10))
    out = Image.new("RGBA", (s + 40, s + 40), (0, 0, 0, 0))
    g = Image.new("RGBA", out.size, (0, 0, 0, 0))
    g.paste(Image.new("RGBA", im.size, (0, 0, 0, 170)), (20, 26), sh)
    out = Image.alpha_composite(out, g)
    out.alpha_composite(im, (20, 20))
    return out

def card_popup():
    if SPEC["popup"].get("img"):  # ready-made picture (e.g. a mock UI idea), Oct 8
        c = Image.open(SPEC["popup"]["img"]).convert("RGBA")
        w = SPEC["popup"].get("w", 620)
        c = c.resize((w, int(c.height * w / c.width)), Image.LANCZOS)
        m = Image.new("L", c.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), 22, fill=255)
        c.putalpha(m)
        return c
    praw, pcrop = RAWS[SPEC["popup"].get("raw", "main")]
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(SPEC["popup"]["src_t"]), "-i", praw, "-frames:v", "1", "-vf", pcrop,
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    fr = Image.fromarray(np.frombuffer(p.stdout, np.uint8).reshape(H, W, 3))
    c = fr.crop(tuple(SPEC["popup"].get("box", [60, 330, 1020, 1580])))
    w = SPEC["popup"].get("w", 620)
    c = c.resize((w, int(c.height * w / c.width)), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), 22, fill=255)
    c.putalpha(m)
    return c

POP = card_popup() if POPUP else None

def title_card():
    t1, t2 = SPEC["title"]["lines"]
    s1, s2 = SPEC["title"].get("sizes", [104, 150])
    l1 = glow_text(t1, s1, (255, 255, 255, 255), ST.get("title_font", FONTB), rad=10)
    l2 = glow_text(t2, s2, ACCENT, ST.get("title_font", FONTB), rad=12)
    im = Image.new("RGBA", (max(l1.width, l2.width), l1.height + l2.height - 70), (0, 0, 0, 0))
    im.alpha_composite(l1, ((im.width - l1.width) // 2, 0))
    im.alpha_composite(l2, ((im.width - l2.width) // 2, l1.height - 70))
    return im

TITLE = title_card() if SPEC.get("title") else None

EMOJI_FONT = "C:/Windows/Fonts/seguiemj.ttf"
emo_cache = {}
def emoji_img(e, size):
    k = (e, size)
    if k not in emo_cache:
        f = ImageFont.truetype(EMOJI_FONT, 220)
        bb = f.getbbox(e)
        im = Image.new("RGBA", (bb[2] - bb[0] + 40, bb[3] - bb[1] + 40), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), e, font=f, embedded_color=True)
        sc = size / max(im.width, im.height)
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        sh = im.split()[3].filter(ImageFilter.GaussianBlur(12))
        out = Image.new("RGBA", (im.width + 60, im.height + 60), (0, 0, 0, 0))
        g = Image.new("RGBA", im.size, (0, 0, 0, 150))
        out.paste(g, (30, 38), sh)
        out.alpha_composite(im, (30, 30))
        emo_cache[k] = out
    return emo_cache[k]

def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im

def make_end_card():
    """Roblox-style game ICON CARD (image + dark panel + big game name), like the end of ref4."""
    E = ECARD
    cw = E.get("w", 600)
    pad = 20
    src = Image.open(E["image"]).convert("RGB")
    iw = cw - 2 * pad
    ih = int(src.height * iw / src.width)
    if ih > iw * 1.05:  # very tall pictures: centre-crop to ~square
        ch = int(src.width * 1.05)
        y0 = (src.height - ch) // 2
        src = src.crop((0, y0, src.width, y0 + ch))
        ih = int(src.height * iw / src.width)
    pic = rounded(src.resize((iw, ih), Image.LANCZOS), 22)
    panel = E.get("panel_h", 210)
    card = Image.new("RGBA", (cw, pad + ih + panel), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, cw - 1, card.height - 1), 34, fill=(24, 32, 52, 250), outline=(8, 10, 16, 255), width=7)
    card.alpha_composite(pic, (pad, pad))
    if E.get("sub"):
        f = font(FONT, 34)
        bb = f.getbbox(E["sub"])
        d.text(((cw - (bb[2] - bb[0])) / 2 - bb[0], pad + ih + panel - 70), E["sub"], font=f, fill=(205, 215, 235, 255))
    # big game name over the lower card (like "Ball Clash")
    lines = E.get("name", [])
    col = tuple(E.get("name_color", [52, 152, 255])) + (255,)
    nf = E.get("font", FONTB)
    imgs = []
    for i, ln in enumerate(lines):
        s = E.get("name_size", 104 if len(lines) > 1 else 120)
        while font(nf, s).getlength(ln) > cw * 1.12 and s > 40:
            s -= 4
        imgs.append(glow_text(ln, s, col if i == len(lines) - 1 else (255, 255, 255, 255), nf, ga=235, rad=10))
    tot = sum(im.height for im in imgs) - 46 * max(0, len(imgs) - 1)
    W2 = max([cw] + [im.width for im in imgs]) + 20
    top_pad = 40
    out = Image.new("RGBA", (W2, card.height + top_pad + max(0, tot - panel // 2)), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.alpha_composite(Image.new("RGBA", card.size, (0, 0, 0, 150)), ((W2 - cw) // 2 + 8, top_pad + 14))
    sh = sh.filter(ImageFilter.GaussianBlur(18))
    out.alpha_composite(sh)
    out.alpha_composite(card, ((W2 - cw) // 2, top_pad))
    y = top_pad + pad + ih + panel // 2 - tot // 2 - 20
    for im in imgs:
        out.alpha_composite(im, ((W2 - im.width) // 2, y))
        y += im.height - 46
    return out

CARD = make_end_card() if ECARD else None

def card_scene(bg, t, t0, dur):
    """game-page hook: blurred gameplay, the card, a green PLAY button, a hand that taps it at ~55 %."""
    base = Image.fromarray(bg).filter(ImageFilter.GaussianBlur(18)).convert("RGBA")
    base = Image.alpha_composite(base, Image.new("RGBA", base.size, (10, 12, 20, 110)))
    k = (t - t0) / max(0.2, dur)
    sc = 0.86 * pop_scale(t0, t, 0.8)
    paste(base, CARD, W / 2, ECARD.get("hook_y", 760), sc)
    by = max(ECARD.get("hook_y", 760) + CARD.height * sc / 2 + 70, CAP_Y + 170)  # PLAY button clear of the caption
    press = 0.55 <= k < 0.7
    bw, bh = int(560 * (0.94 if press else 1)), int(130 * (0.94 if press else 1))
    btn = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((0, 0, bw - 1, bh - 1), 28, fill=(45, 160, 75, 255) if not press else (35, 130, 60, 255))
    bd.polygon([(bw / 2 - 26, bh / 2 - 34), (bw / 2 - 26, bh / 2 + 34), (bw / 2 + 34, bh / 2)], fill="white")
    paste(base, btn, W / 2, by)
    # hand moves in from bottom-right, taps
    hx0, hy0, hx1, hy1 = 900, 1700, W / 2 + 40, by + 70
    m = min(1.0, k / 0.55)
    m = 1 - (1 - m) ** 3
    hx, hy = hx0 + (hx1 - hx0) * m, hy0 + (hy1 - hy0) * m
    paste(base, emoji_img("👆", 190 if press else 210), hx, hy)
    return np.asarray(base.convert("RGB"))

def paste(base, im, cx, cy, scale=1.0):
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def pop_scale(t0, t, a=0.82):
    k = min(1.0, max(0.0, (t - t0) / 0.1))
    return a + (1 - a) * (1 - (1 - k) ** 3)

def word_at(t):
    for i, w in enumerate(words):
        nxt = words[i + 1][0] if i + 1 < len(words) else TOTAL
        if w[0] - 0.02 <= t < max(nxt, w[1]) - 0.0:
            return i
    return None

# ---------------------------------------------------------------- render
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
                        "-pix_fmt", "yuv420p", WORK + "video.mp4"], stdin=subprocess.PIPE)
def _key(i):
    k = SHOTS[i][3] if len(SHOTS[i]) > 3 else "main"
    return "main" if k == "CARD" else k
frames = [read_shot(SHOTS[i][1], b - a, _key(i)) for i, (a, b) in enumerate(bounds)]

def zoomed(a, z):
    cw, ch = int(W / z), int(H / z)
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    return np.asarray(Image.fromarray(a[y0:y0 + ch, x0:x0 + cw]).resize((W, H), Image.BILINEAR))

def hblur(a, k):
    acc = a.astype(np.float32)
    for s in range(1, k):
        acc += np.roll(a, s * 11, axis=1)
    return (acc / k).astype(np.uint8)
WH = 4  # whip frames (~0.13 s)

def vblur(a, k):
    acc = a.astype(np.float32)
    for s in range(1, k):
        acc += np.roll(a, s * 9, axis=0)
    return (acc / k).astype(np.uint8)

for fi in range(NF):
    t = fi / FPS
    si = max(i for i, (a, b) in enumerate(bounds) if a <= t + 1e-6)
    a, b = bounds[si]
    loc = min(len(frames[si]) - 1, int((t - a) * FPS))
    img = frames[si][loc]
    if KB:  # slow push-in over the shot (cinematic, hides the bot-cam stiffness)
        z = 1 + KB * min(1.0, (t - a) / max(0.5, b - a))
        cw, ch = int(W / z), int(H / z)
        x0, y0 = (W - cw) // 2, (H - ch) // 2
        img = np.asarray(Image.fromarray(img[y0:y0 + ch, x0:x0 + cw]).resize((W, H), Image.BILINEAR))
    if len(SHOTS[si]) > 3 and SHOTS[si][3] == "CARD" and CARD is not None:
        img = card_scene(img, t, a, b - a)
    tr = SHOTS[si][2]
    tr = TRANS if tr is True or tr == 1 else (tr if isinstance(tr, str) else None)
    if tr == "rzoom" and loc < 6:
        # radial zoom-blur punch-in (ref4 opening / narrator entrances)
        s = 1 - loc / 6
        zs = [1.0 + s * 0.42 * j / 3 for j in range(4)]
        img = (sum(zoomed(img, z).astype(np.float32) for z in zs) / len(zs)).astype(np.uint8)
        img = zoomed(img, 1 + 0.18 * s)
    elif tr == "hwhip" and si > 0 and loc < WH:
        # new shot slides in from the right with heavy horizontal smear (ref4 0.95 s / 14.2 s)
        k = (loc + 1) / (WH + 1)
        off = int(W * (1 - k) ** 1.6)
        prev = frames[si - 1][min(len(frames[si - 1]) - 1, max(0, int((bounds[si - 1][1] - bounds[si - 1][0]) * FPS) - 1))]  # last SHOWN frame (not the read-ahead pad)
        comp = img.copy()
        if off:
            comp[:, :W - off] = prev[:, off:]
            comp[:, W - off:] = img[:, :off]
            comp = hblur(comp, 8)
        img = comp
    elif tr == "wflash" and si > 0 and loc < 5:
        k = [1.0, 0.85, 0.55, 0.28, 0.1][loc]
        img = (img.astype(np.float32) * (1 - k) + 255 * k).astype(np.uint8)
    elif tr and si > 0 and tr != "cut":
        if tr == "whip" and loc < WH:
            # reference transition: new shot slides DOWN from the top with heavy vertical motion blur
            k = (loc + 1) / (WH + 1)
            off = int(H * (1 - k) ** 1.6)
            prev = frames[si - 1][min(len(frames[si - 1]) - 1, max(0, int((bounds[si - 1][1] - bounds[si - 1][0]) * FPS) - 1))]  # last SHOWN frame (not the read-ahead pad)
            comp = img.copy()
            if off:
                comp[off:] = prev[:H - off]
                comp[:off] = img[H - off:]
                comp = vblur(comp, 7)
            img = comp
        elif tr == "flash" and loc < 5:
            k = 1 - loc / 5
            img = (img.astype(np.float32) * (1 - k) + 255 * k).astype(np.uint8)
        elif tr == "zoom" and loc < 6:
            z = 1.35 - 0.35 * (loc / 6) ** 0.6
            cw, ch = int(W / z), int(H / z)
            x0, y0 = (W - cw) // 2, (H - ch) // 2
            img = np.asarray(Image.fromarray(img[y0:y0 + ch, x0:x0 + cw]).resize((W, H), Image.BILINEAR))
            if loc < 3:
                img = ((img.astype(np.float32) + np.roll(img, 6, 0) + np.roll(img, -6, 0)) / 3).astype(np.uint8)
        elif tr == "slide" and loc < 6:
            k = (loc + 1) / 7
            off = int(W * (1 - k) ** 2)
            prev = frames[si - 1][min(len(frames[si - 1]) - 1, max(0, int((bounds[si - 1][1] - bounds[si - 1][0]) * FPS) - 1))]  # last SHOWN frame (not the read-ahead pad)
            if off:
                comp = np.empty_like(img)
                comp[:, :W - off] = prev[:, off:]
                comp[:, W - off:] = img[:, :off]
                img = comp
    base = Image.fromarray(img).convert("RGBA")
    # meme popup (bottom-right, pops in)
    if POPUP and words[POPUP[0]][0] <= t < words[POPUP[1]][1] + 0.15:
        paste(base, POP, W - 30 - POP.width / 2, SPEC['popup'].get('y', 1290), pop_scale(words[POPUP[0]][0], t, 0.6))
    # countdown numerals
    for wi, txt in COUNT.items():
        nxt = min([words[x][0] for x in COUNT if x > wi] + [words[max(COUNT) + 2][0]])
        if words[wi][0] <= t < nxt:
            paste(base, glow_text(txt, 300, (255, 255, 255, 255), FONTB, rad=12) if txt not in cap_cache else cap_cache[txt],
                  W / 2, 900, pop_scale(words[wi][0], t, 0.7))
    # stickers
    for wi, kind in STICK.items():
        if words[wi][0] <= t < words[wi][0] + STICK_DUR:
            paste(base, icon(kind), W / 2, STICK_Y, pop_scale(words[wi][0], t, 0.5))
    # emoji sticker pop-ups (ref4: cherries on "balls")
    for wi, e in EMOJI.items():
        t0e = words[wi][0]
        dur = e.get("dur", 0.65)
        if t0e <= t < t0e + dur:
            im = emoji_img(e["e"], e.get("size", 460))
            if t > t0e + dur - 0.12:  # quick fade/blur out
                f = (t0e + dur - t) / 0.12
                im = im.copy()
                im.putalpha(im.split()[3].point(lambda v: int(v * max(0, f))))
            paste(base, im, e.get("x", W / 2), e.get("y", 900), pop_scale(t0e, t, 0.4))
    # end: game name pops up like the reference's game-icon popup
    if TITLE is not None and t >= words[SPEC['title']['word']][0]:
        paste(base, TITLE, W / 2, TITLE_Y, pop_scale(words[SPEC['title']['word']][0], t, 0.55))
    ecard_on = False
    if CARD is not None and t >= words[ECARD["word"]][0] + ECARD.get("delay", 0):
        t0c = words[ECARD["word"]][0] + ECARD.get("delay", 0)
        im = CARD
        if t - t0c < 0.12:  # blurry pop-in like ref4
            im = CARD.filter(ImageFilter.GaussianBlur(10 * (1 - (t - t0c) / 0.12)))
        paste(base, im, W / 2, ECARD.get("y", 900), pop_scale(t0c, t, 0.55))
        ecard_on = ECARD.get("hide_caps", True)
    # one word at a time
    w = word_at(t)
    if ecard_on:
        w = None
    if w is not None and t > words[w][1] + ST.get("cap_hold", 99):  # optional: hide a word during long pauses
        w = None
    if w is not None:
        cy = CAP_Y
        if len(SHOTS[si]) > 3 and SHOTS[si][3] in CAP_Y_KEY:  # e.g. shop UI shots: caption below the window
            cy = CAP_Y_KEY[SHOTS[si][3]]
        paste(base, caption(words[w][2]), W / 2, cy, pop_scale(words[w][0], t, 0.86))
    enc.stdin.write(np.asarray(base.convert("RGB")).tobytes())
enc.stdin.close()
enc.wait()

# ---------------------------------------------------------------- audio: voice + music bed + sfx
def mean_db(p):
    o = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(o.split("mean_volume:")[1].split("dB")[0])
MUSIC = ST.get("music")
if MUSIC:   # royalty-free track (incompetech, CC-BY) instead of the reference stem
    BED = MUSIC
    bed_len = 1e9
    tempo = 1.0
    under = ST.get("music_under", 13.0)
else:
    bed_len = 19.156
    tempo = min(1.0, max(0.5, bed_len / TOTAL))
    under = 6.7
gv, gb = mean_db(vo), mean_db(BED)
bed_gain = (gv - under) - gb
ins = ["-i", WORK + "video.mp4", "-i", vo, "-ss", str(ST.get("music_ss", 0)), "-i", BED]
fc = (f"[1:a]aresample=48000,apad[v];[2:a]aresample=48000,atempo={tempo:.4f},volume={bed_gain:.2f}dB,"
      f"afade=t=out:st={max(0, TOTAL - 0.6):.2f}:d=0.6,apad[m];")
mix = ["[v]", "[m]"]
# sfx: on every transition (style "sfx_trans") + on chosen words ("sfx": {word index: file})
SFXD = V + "sfx/"
MEME = V + "memesfx/"
hits = []
if ST.get("sfx_trans"):
    for i, (a, b) in enumerate(bounds):
        tr = SHOTS[i][2]
        if i > 0 and tr and tr != "cut":
            hits.append((a - 0.05, ST["sfx_trans"], ST.get("sfx_trans_db", -10)))
for k, v in ST.get("sfx", {}).items():
    f, db = (v, -6) if isinstance(v, str) else (v[0], v[1])
    hits.append((words[int(k)][0], f, db))
for n, (at, f, db) in enumerate(hits):
    p = f if os.path.isabs(f) or ":" in f else (SFXD + f if os.path.exists(SFXD + f) else MEME + f)
    ins += ["-i", p]
    fc += f"[{3 + n}:a]aresample=48000,volume={db}dB,adelay={int(max(0, at) * 1000)}:all=1,apad[s{n}];"
    mix.append(f"[s{n}]")
fc += f"{''.join(mix)}amix=inputs={len(mix)}:duration=longest:normalize=0,atrim=0:{TOTAL:.3f},alimiter=limit=0.95[a]"
subprocess.run(["ffmpeg", "-v", "error", "-y"] + ins + ["-filter_complex", fc,
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], check=True)
print("OUT", OUT, round(TOTAL, 2), "s  music", os.path.basename(BED), "sfx", len(hits), "trans", TRANS)
