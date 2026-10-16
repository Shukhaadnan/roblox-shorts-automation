"""Daily poster (sir, Oct 11): ONE video per released game per day, on TikTok + YouTube + Instagram.
usage: python post_daily.py <game_key>     (steal_a_pet | secret_game | tilt)
Picks the oldest entry in videos/post_queue.json with "daily": "<game_key>" that is not posted on YT yet,
runs post_seq.py on it, prints a short report (delivered to sir by the no-agent cron).
Never posts A Quiet Place (quiet_place) - sir: not yet."""
import json, os, subprocess, sys
R = "./"
game = sys.argv[1]
if game == "quiet_place":
    print("Skipped: A Quiet Place videos are on hold (sir)."); raise SystemExit
q = json.load(open(R + "videos/post_queue.json", encoding="utf-8"))
import datetime
today = datetime.date.today().isoformat()
if any(x.get("game") == game and any(str(x.get("posted_" + p, "")).startswith(today) for p in ("tt", "yt", "ig")) for x in q):
    raise SystemExit  # already posted this game today (1 per game per day) - stay silent
# ONLY 1 YouTube Short per day across ALL games (sir, Oct 15: two went to YT that day).
# YouTube rotates by date - Extreme Tilt every other day (newest game, gets the push); the others share the rest.
YT_ROTA = ["tilt", "steal_a_pet", "tilt", "secret_game"]
yt_game = YT_ROTA[(datetime.date.today().toordinal() + 3) % len(YT_ROTA)]  # Oct 16 (Tilt launch day) = tilt
yt_used = any(str(x.get("posted_yt", "")).startswith(today) for x in q)
yt_today = (game == yt_game) and not yt_used
# pending = not yet posted anywhere it is still due (TT/IG done + YT skipped = finished)
def done(i, p): return str(i["status"].get(p, "")).startswith(("ok", "skip"))
todo = [i for i in q if i.get("daily") == game and os.path.exists(i["file"])
        and not (done(i, "yt") or (done(i, "tt") and done(i, "ig")))]
names = {"steal_a_pet": "Steal a Pet", "secret_game": "Everybody Has a Secret", "tilt": "Extreme Tilt"}
if not todo:
    print(f"No {names.get(game, game)} video ready to post today sir - queue is empty, making more.")
    raise SystemExit
i = todo[0]
F = os.path.basename(i["file"])
plats = [p for p in ("tt", "yt", "ig") if not done(i, p) and (p != "yt" or yt_today)]
if not plats:
    raise SystemExit  # only YouTube left for this video and today isn't its YT day - try tomorrow, stay silent
env = dict(os.environ, SEQ_PLATS=",".join(plats))
# stdin=DEVNULL: the no-agent cron has no stdin handle (WinError 6 "handle is invalid" on Oct 15)
subprocess.run([sys.executable, "post_seq.py", "0", F], cwd=R + "tools", env=env, stdin=subprocess.DEVNULL,
               stdout=open(R + "growth/post_daily.out", "a"), stderr=subprocess.STDOUT, timeout=3 * 3600)
q = json.load(open(R + "videos/post_queue.json", encoding="utf-8"))
i = [x for x in q if os.path.basename(x["file"]) == F][0]
if not yt_today and not done(i, "yt"):
    i["status"]["yt"] = "skip (1 YouTube/day - not this game's YT day)"
    json.dump(q, open(R + "videos/post_queue.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
s = i["status"]
left = len(todo) - 1
print(f"Posted {names.get(game, game)} vid sir: \"{i['hook']}\"")
print("TikTok: " + str(s.get("tt", "-")).split(" ")[0])
yt = str(s.get("yt", "-"))
print("YouTube: " + (yt.split(" ")[1] if yt.startswith("ok") and len(yt.split(" ")) > 1 else yt.split(" ")[0]))
print("Instagram: " + str(s.get("ig", "-")).split(" ")[0])
print(f"{left} more {names.get(game, game)} vids queued")
