"""Extreme Tilt launch shorts: generate + whisper-check the voice takes. usage: python tilt5_vo.py [names...]
Voice = same cloned narrator as the SAP / EHAS shorts (clone:ref1:fast). Every script says the full game name "Extreme Tilt".
"""
import json, os, sys, re, difflib
sys.path.insert(0, r"./tts")
import tts_words, soundfile as sf, numpy as np

V = "./videos/reelcopy/"
SCRIPTS = {
    # 1 HUNTER: push bot after bot off the plate
    "tilt5_hunter": "In this Roblox game, there's only one rule. Push everyone off the plate. So I walked up to the first guy and shoved him into the sky. Then the next one. And the next one. They didn't even see me coming! Last one standing wins. Save this video and follow for more. The game is called Extreme Tilt!",
    # 2 WHIFF: miss a push and trip yourself off
    "tilt5_whiff": "In this Roblox game, you can push anyone off the plate. But here's the catch. If you miss, you trip. I tried to push a guy right at the edge, he stepped away, and I flew off the plate instead. Worst push ever. Save this video and follow for more. The game is called Extreme Tilt!",
    # 3 NUKE: piano, then nuke the whole server
    "tilt5_nuke": "Everyone on this plate was trying to push me off. So first, I dropped a piano on them. That made it tip. But they were still there. So I bought a nuke. Three, two, one. The whole server got blasted into the sky, and I was the only one left standing. Save this video and follow for more. The game is called Extreme Tilt!",
    # 4 GHOST: fall off early, come back as a ghost and get revenge
    "tilt5_ghost": "I slipped off the plate in the first ten seconds. But in this game, falling isn't the end. You come back as a ghost, and you can drop junk on everyone who's still alive. So I started raining boots and fish on them. Revenge is sweet. Save this video and follow for more. The game is called Extreme Tilt!",
    # 5 SURVIVE: the plate fights back (lurches, quakes, breaking edges)
    "tilt5_survive": "This plate is trying to kill you. It leans to one side out of nowhere. Then an earthquake hits. Then the edges start breaking off, and the plate keeps getting smaller and smaller. One wrong step and you're gone. Can you survive till the end? Save this video and follow for more. The game is called Extreme Tilt!",
}


def norm(s):
    return [x for x in (re.sub(r"[^a-z0-9]", "", w.lower()) for w in s.split()) if x]


if __name__ == "__main__":
    names = sys.argv[1:] or list(SCRIPTS)
    for n in names:
        text = SCRIPTS[n]
        d = V + n + "/"
        os.makedirs(d, exist_ok=True)
        words = tts_words.synth(text, d + "vo.wav", "clone:ref1:fast", 1.18)
        json.dump({"text": text, "words": words}, open(d + "vo_words.json", "w"))
        data, sr = sf.read(d + "vo.wav", dtype="float32")
        if data.ndim > 1:
            data = data.mean(1)
        n16 = int(len(data) * 16000 / sr)
        a16 = np.interp(np.linspace(0, len(data) - 1, n16), np.arange(len(data)), data).astype(np.float32)
        segs, _ = tts_words._w().transcribe(a16, language="en", beam_size=5)
        heard = " ".join(s.text.strip() for s in segs)
        ratio = difflib.SequenceMatcher(None, norm(text), norm(heard)).ratio()
        print(n, "dur", round(len(data) / sr, 2), "words", len(words), "ratio", round(ratio, 3))
        print("   heard:", heard[-90:], flush=True)
