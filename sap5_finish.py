"""final QA + delivery for the sap5 batch: whisper the final mix, loudness, discord copy. usage: python sap5_finish.py <name> [...]"""
import json, os, re, subprocess, sys, difflib, shutil
sys.path.insert(0, r"./tts")
import tts_words, numpy as np

V = "./videos/"

def norm(s):
    return [x for x in (re.sub(r"[^a-z0-9]", "", w.lower()) for w in s.split()) if x]

for n in sys.argv[1:]:
    src = V + "nocard/" + n + ".mp4"
    spec = json.load(open("./tools/reels/" + n + ".json", encoding="utf-8"))
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    a16 = np.frombuffer(pcm, np.float32)
    segs, _ = tts_words._w().transcribe(a16, language="en", beam_size=5)
    heard = " ".join(s.text.strip() for s in segs)
    a, b = norm(spec["script"]), norm(heard)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    lo = subprocess.run(["ffmpeg", "-hide_banner", "-i", src, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float([l for l in lo.split("\n") if l.strip().startswith("I:")][-1].split()[1])
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,codec_type:format=duration", "-of", "json", src], capture_output=True, text=True).stdout)
    v = [s for s in pr["streams"] if s["codec_type"] == "video"][0]
    dur = float(pr["format"]["duration"])
    dst = V + n + ".mp4"
    # gain-normalise to -16 LUFS (limiter keeps peaks under -1 dBTP); video stream copied untouched
    gain = -16.0 - I
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:level=false",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst], check=True)
    lo = subprocess.run(["ffmpeg", "-hide_banner", "-i", dst, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    I = float([l for l in lo.split("\n") if l.strip().startswith("I:")][-1].split()[1])
    src = dst
    os.makedirs(V + "discord", exist_ok=True)
    dc = V + "discord/" + n + ".mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=720:1280:flags=lanczos", "-c:v", "libx264", "-crf", "23",
                    "-maxrate", "3.2M", "-bufsize", "6.4M", "-preset", "slow", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dc], check=True)
    mb = os.path.getsize(dc) / 1e6
    res = {"name": n, "dur": round(dur, 2), "wh": f'{v["width"]}x{v["height"]}', "lufs": I, "whisper_ratio": round(ratio, 3),
           "discord_mb": round(mb, 2), "heard": heard}
    json.dump(res, open(V + "reelcopy/" + n + "/final_qa.json", "w"), indent=1)
    print(json.dumps(res), flush=True)
