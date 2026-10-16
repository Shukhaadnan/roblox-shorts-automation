"""make_short.py - raw Roblox demo recording -> polished 9:16 60fps Short.
Usage: <tts venv python> make_short.py <spec.json>
spec: raw, out, rotate (true if recorded on the portrait-rotated screen), crop [x,y,w,h] (after rotation),
      voice (kokoro id), speed, segments [{src:[a,b], vo, title?, max_speed?}]
Voice: Kokoro (offline, natural) with whisper word timings -> word-by-word pop captions.
"""
import json, os, subprocess, sys, tempfile
sys.path.insert(0, r"./tts")
import tts_words

FF = "ffmpeg"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg failed:\n" + r.stderr[-1500:])


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def build_ass(words, titles, path, cap_y):
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Arial Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,10,5,5,60,60,0,1
Style: Title,Arial Black,70,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,7,4,8,40,40,70,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev, chunks, cur = [], [], []
    for w in words:
        cur.append(w)
        if len(cur) == 3 or w[2].endswith((".", "!", "?", ",")):
            chunks.append(cur); cur = []
    if cur:
        chunks.append(cur)
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0][0] if ci + 1 < len(chunks) else ch[-1][1] + 0.35
        for wi, w in enumerate(ch):
            st = w[0]
            en = ch[wi + 1][0] if wi + 1 < len(ch) else max(w[1], min(nxt, w[1] + 0.45))
            if en <= st:
                continue
            parts = []
            for k, x in enumerate(ch):
                txt = x[2].upper().replace("{", "").replace("}", "")
                if k == wi:
                    parts.append(r"{\c&H0000E6FF&\fscx112\fscy112}" + txt + r"{\c&H00FFFFFF&\fscx100\fscy100}")
                else:
                    parts.append(txt)
            # shrink long chunks so they always fit: measure real Arial Black width (incl. 112% active word + outline)
            from PIL import ImageFont
            _f = ImageFont.truetype("C:/Windows/Fonts/ariblk.ttf", 96)
            # libass renders Arial Black ~0.75x the PIL width at the same size
            wpx = (sum(_f.getlength(x[2].upper()) for x in ch) + _f.getlength(" ") * (len(ch) - 1)) * 0.75
            wpx += max(_f.getlength(x[2].upper()) for x in ch) * 0.75 * 0.12 + 40
            fs = min(100, int(980 / max(1.0, wpx) * 100))
            pop = r"{\pos(540," + str(cap_y) + r")\fs" + str(int(96 * fs / 100)) + (r"\fscx80\fscy80\t(0,90,\fscx100\fscy100)" if wi == 0 else "") + "}"
            ev.append(f"Dialogue: 1,{ass_time(st)},{ass_time(en)},Cap,,0,0,0,,{pop}{' '.join(parts)}")
    for st, en, txt, col in titles:
        ev.append(f"Dialogue: 2,{ass_time(st)},{ass_time(en)},Title,,0,0,0,,{{\\fad(150,150)\\c{col}}}{txt}")
    open(path, "w", encoding="utf-8").write(hdr + "\n".join(ev) + "\n")


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    work = tempfile.mkdtemp(prefix="short_", dir=os.environ.get("TMPDIR"))
    voice, vspeed = spec.get("voice", "am_michael"), spec.get("speed", 1.12)
    x, y, w, h = spec["crop"]
    rot = "transpose=1," if spec.get("rotate") else ""
    # gameplay scaled to full width; blurred copy fills the bands above/below
    gh = int(round(h * 1080 / w / 2) * 2)
    top = int(spec.get("top", (1920 - gh) // 2))
    clips, words_all, titles, tc = [], [], [], 0.0
    for i, seg in enumerate(spec["segments"]):
        wav = os.path.join(work, f"vo{i}.wav")
        words = tts_words.synth(seg["vo"], wav, voice, vspeed)
        seg_len = max(dur(wav) + seg.get("pad", 0.2), 1.0)
        a, b = seg["src"]
        speed = (b - a) / seg_len
        mx = seg.get("max_speed", 1.35)
        if speed > mx:  # never fast-forward too hard (looks laggy) -> use the END of the window
            a = b - seg_len * mx; speed = mx
        if speed < seg.get("min_speed", 0.8):  # never slow-mo too hard either -> extend source window
            ms = seg.get("min_speed", 0.8)
            b = a + seg_len * ms; speed = ms
        vf = (f"[0:v]trim={a:.3f}:{b:.3f},setpts=(PTS-STARTPTS)/{speed:.4f},{rot}crop={w}:{h}:{x}:{y},split[s1][s2];"
              f"[s1]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=28,eq=brightness=-0.12:saturation=1.2[bg];"
              f"[s2]scale=1080:{gh}:flags=lanczos,eq=saturation=1.12:contrast=1.04,unsharp=5:5:0.6[fg];"
              f"[bg][fg]overlay=0:{top},fps=60,trim=0:{seg_len:.3f},setpts=PTS-STARTPTS[v]")
        out = os.path.join(work, f"seg{i}.mp4")
        run([FF, "-y", "-v", "error", "-i", seg.get("raw", spec["raw"]), "-i", wav, "-filter_complex",
             vf + f";[1:a]aresample=48000,apad,atrim=0:{seg_len:.3f}[a]", "-map", "[v]", "-map", "[a]",
             "-c:v", "h264_nvenc", "-preset", "p6", "-rc", "vbr", "-cq", "17", "-b:v", "0",
             "-c:a", "aac", "-ar", "48000", out])
        clips.append(out)
        words_all += [(s + tc, e + tc, t) for s, e, t in words]
        if seg.get("title"):
            titles.append((tc, tc + seg_len, seg["title"], seg.get("title_color", "&H0000E6FF&")))
        tc += seg_len
        print(f"seg{i}: {seg_len:.1f}s speed {speed:.2f}")
    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
    joined = os.path.join(work, "joined.mp4")
    run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    ass = os.path.join(work, "caps.ass")
    build_ass(words_all, titles, ass, spec.get("cap_y", 1180))
    ass_ff = ass.replace("\\", "/").replace(":", "\\:")
    run([FF, "-y", "-v", "error", "-i", joined, "-vf", f"ass='{ass_ff}'",
         "-c:v", "h264_nvenc", "-preset", "p7", "-rc", "vbr", "-cq", "21", "-b:v", "0", "-maxrate", "6M", "-bufsize", "12M",
         "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", spec["out"]])
    print(f"DONE {spec['out']} {tc:.1f}s")


if __name__ == "__main__":
    main()
