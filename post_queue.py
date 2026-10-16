"""post_queue.py - NO-AI poster for sir's prepared videos (zero Claude usage).
Queue: ./videos/post_queue.json
  python post_queue.py add <video> <game_key> "<hook>"   add a finished video (captions are generated)
  python post_queue.py slot [N]    launch a detached run that posts up to N videos (used by peak-time cron)
  python post_queue.py run [N]     post now (blocking); writes a report to growth/post_reports/
  python post_queue.py report      print reports not yet delivered (cron watchdog; silent if none)
  python post_queue.py status      print the queue
Posts each video to YouTube Shorts, TikTok and Instagram via tools/uploader.py (sir's logged-in Chrome).
Waits for the PC to be idle (no keyboard/mouse 3+ min) and for no Studio recording before driving Chrome.
"""
import json, os, sys, time, datetime, subprocess, glob, re

R = "./"
Q = R + "videos/post_queue.json"
REP = R + "growth/post_reports/"
LOCK = R + "videos/.post_lock"
sys.path.insert(0, R + "tools")
GAMES = {
    "steal_a_pet": ("Steal a Pet 2.0", 104938688727960, "#stealapet #stealabrainrot"),
    "nights_forest": ("Wolfpack: 99 Nights in the Woods", 118141248008355, "#99nights #99nightsintheforest"),
    "blade_ball": ("Parry King: Blade Ball Arena", 120375526854160, "#bladeball"),
    "speed_escape": ("Zoomies: +1 Speed Escape", 114957991573074, "#speedescape #escape"),
    "ride_a_pet": ("Dragon Riders: Ride & Hatch Pets", 131189886345972, "#rideapet #pets"),
}
PLATS = ["yt", "tt", "ig"]


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def load():
    return json.load(open(Q, encoding="utf-8")) if os.path.exists(Q) else []


def save(q):
    json.dump(q, open(Q, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def add(video, game, hook):
    name, pid, tags = GAMES[game]
    link = f"https://www.roblox.com/games/{pid}"
    q = load()
    if any(os.path.basename(i["file"]) == os.path.basename(video) for i in q):
        print("already queued"); return
    q.append({
        "file": os.path.abspath(video).replace("/", "\\"), "game": game, "hook": hook, "added": now(),
        "yt_title": f"{hook} 💀 {name} #shorts"[:95],
        "yt_desc": f"{hook} 💀\n\nPlay: {name} by SkyipsCreator\n{link}\nOpen Roblox, search \"{name}\" and pick the one by SkyipsCreator\n\n#roblox #shorts #fyp #funny {tags}",
        "caption": f"{hook} 💀\n\nPlay \"{name}\" by SkyipsCreator (link in bio)\n#roblox #fyp #funny #robloxfunny {tags}",
        "status": {"tt": "manual (sir uploads TikTok by hand)"}, "tries": {},
    })
    save(q)
    print(f"queued {os.path.basename(video)} ({len([i for i in q if not done(i)])} waiting)")


def done(i):
    return all(i["status"].get(p, "").startswith(("ok", "unverified", "gave up", "manual")) for p in PLATS)


def idle_ms():
    ps = ("Add-Type 'using System;using System.Runtime.InteropServices;public class IdleX{[StructLayout(LayoutKind.Sequential)]"
          "struct L{public uint cb;public uint t;}[DllImport(\"user32.dll\")]static extern bool GetLastInputInfo(ref L l);"
          "public static uint Ms(){L l=new L();l.cb=8;GetLastInputInfo(ref l);return (uint)Environment.TickCount-l.t;}}'; [IdleX]::Ms()")
    try:
        return int(subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60).stdout.strip())
    except Exception:
        return 10 ** 9


def wait_free(max_min=45):
    for _ in range(max_min):
        if not os.path.isdir(R + "videos/.rec_lock") and idle_ms() > 180000:
            return True
        time.sleep(60)
    return False


def post_yt(u, i):
    r = u.yt(i["file"], i["yt_title"], i["yt_desc"])
    if "PUB false" in r:  # visibility step didn't stick -> redo the wizard in the still-open dialog
        put = "function put(el,s){el.focus();document.execCommand('selectAll',false,null);document.execCommand('insertText',false,s);}"
        u.js("javascript:(function(){" + put + "var t=document.querySelectorAll('#textbox');if(t.length>=2){put(t[1]," + json.dumps(i["yt_desc"]) + ");}"
             "var r=document.querySelector('tp-yt-paper-radio-button[name=\"VIDEO_MADE_FOR_KIDS_NOT_MFK\"]');if(r){r.click();}document.title='FIX';})()", 3)
        for _ in range(3):
            u.sh("bash chrome.sh js js_yt_next.txt 3")
        r += " || " + u.sh("bash chrome.sh js js_yt_public.txt 2; bash chrome.sh title") + " " + u.sh("bash chrome.sh js js_yt_done.txt 8; bash chrome.sh title")
    if "youtube.com/shorts/" in r and ("PUB true" in r or "|| PUB true" in r):
        return "ok " + "https://youtube.com/shorts/" + r.split("youtube.com/shorts/")[1].split()[0]
    if "youtube.com/shorts/" in r:
        return "unverified (uploaded, visibility unclear) https://youtube.com/shorts/" + r.split("youtube.com/shorts/")[1].split()[0]
    return "fail " + r[-160:]


def post_tt(u, i):
    # optional per-item TikTok version + native TikTok sound (sir, Oct 6): tt_file = no-music cut, tt_sound = search query
    env = {}
    if i.get("tt_sound"):
        env = {"TT_SOUND": i["tt_sound"], "TT_SOUND_DB": str(i.get("tt_sound_db", -14)), "TT_SOUND_IDX": str(i.get("tt_sound_idx", 0))}
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        r = u.tt(i.get("tt_file", i["file"]), i["hook"], i["caption"])
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    time.sleep(25)
    u.sh('bash chrome.sh go "https://www.tiktok.com/tiktokstudio/content" 15')
    snip = i["hook"][:22]
    c = u.js("javascript:(function(){var t=document.body.innerText;document.title='TTCHK '+(t.indexOf(" + json.dumps(snip) + ")>=0)+' n='+t.length;})()", 2)
    if "TTCHK true" in c:
        m = re.search(r"sound added: [^|]+", r)
        return "ok" + (" | " + m.group(0).strip() if m else (" | NO SOUND" if i.get("tt_sound") else ""))
    if "Something went wrong" in r or "up=Uploaded" not in r:
        return "fail " + r[-120:]
    return "unverified (posted, not seen in content list yet)"


def post_ig(u, i):
    r = u.ig(i["file"], i["hook"], i["caption"])
    return "ok" if "shared" in r.lower() else "fail " + r[-120:]


def run(n):
    try:
        os.mkdir(LOCK)
    except FileExistsError:
        return
    lines = []
    try:
        q = load()
        todo = [i for i in q if not done(i) and os.path.exists(i["file"])][:n]
        if not todo:
            return
        if not wait_free():
            lines.append("Skipped this peak slot: the PC was in use the whole time. Will post next slot.")
            return
        import uploader as u
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "if(-not (Get-Process chrome -EA SilentlyContinue | ? MainWindowTitle)){Start-Process chrome '--start-maximized'; Start-Sleep 6}"])
        fns = {"yt": post_yt, "tt": post_tt, "ig": post_ig}
        for k, i in enumerate(todo):
            res = []
            for p in PLATS:
                st = i["status"].get(p, "")
                if st.startswith(("ok", "unverified", "gave up", "manual")):
                    continue
                if idle_ms() < 60000:  # sir grabbed the mouse/keyboard -> stop, continue next slot
                    lines.append("Paused: sir started using the PC.")
                    save(q); return
                try:
                    out = fns[p](u, i)
                except Exception as e:
                    out = f"fail {e}"
                i["tries"][p] = i["tries"].get(p, 0) + 1
                if out.startswith("fail") and i["tries"][p] >= 2:
                    out = "gave up: " + out
                i["status"][p] = out
                i["posted_" + p] = now()
                save(q)
                res.append(f"{p.upper()} {out.split(' ')[0]}")
                time.sleep(60)
            lines.append(f"- {os.path.basename(i['file'])}: " + ", ".join(res))
            if k < len(todo) - 1:
                time.sleep(180)
    finally:
        if lines:
            os.makedirs(REP, exist_ok=True)
            left = len([i for i in load() if not done(i)])
            hdr = f"Posted at peak time ({now()}), {left} still in queue:"
            open(REP + datetime.datetime.now().strftime("%Y%m%d_%H%M") + ".txt", "w", encoding="utf-8").write(hdr + "\n" + "\n".join(lines))
        try:
            os.rmdir(LOCK)
        except OSError:
            pass


def report():
    for f in sorted(glob.glob(REP + "*.txt")):
        print(open(f, encoding="utf-8").read().strip())
        os.replace(f, f[:-4] + ".sent")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "add":
        add(a[1], a[2], a[3])
    elif a[0] == "slot":
        n = a[1] if len(a) > 1 else "5"
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "run", n], cwd=R + "tools",
                         creationflags=0x00000008 | 0x00000200, close_fds=True,
                         stdout=open(R + "growth/post_queue.log", "a"), stderr=subprocess.STDOUT)
    elif a[0] == "run":
        run(int(a[1]) if len(a) > 1 else 5)
    elif a[0] == "report":
        report()
    elif a[0] == "status":
        for i in load():
            print(os.path.basename(i["file"]), i["status"])
