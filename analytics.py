#!/usr/bin/env python
"""Analytics loop: collect public stats -> growth/analytics.json history -> score formats.
Usage: python tools/analytics.py collect | report
YouTube: public @SkyipsCreator/shorts page (no login). Each video is mapped to a FORMAT tag so winners/losers
are judged per format, not per video."""
import json, re, sys, os, time, urllib.request, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = os.path.join(ROOT, "growth")
HIST = os.path.join(G, "analytics.json")
FMT = os.path.join(G, "formats.json")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
       "Accept-Language": "en-US,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"}

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read().decode("utf-8", "replace")

def init_data(html):
    i = html.index("var ytInitialData = ") + len("var ytInitialData = ")
    return json.JSONDecoder().raw_decode(html[i:])[0]

def walk(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key: yield v
            yield from walk(v, key)
    elif isinstance(o, list):
        for v in o: yield from walk(v, key)

def views_num(s):
    m = re.search(r"([\d.,]+)\s*([KkMm]?)", s or "")
    if not m: return 0
    n = float(m.group(1).replace(",", ""))
    return int(n * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1))

def yt_shorts():
    d = init_data(get("https://www.youtube.com/@SkyipsCreator/shorts"))
    out = []
    for v in walk(d, "shortsLockupViewModel"):
        om = v.get("overlayMetadata", {})
        title = om.get("primaryText", {}).get("content", "")
        vtxt = om.get("secondaryText", {}).get("content", "")
        vid = ""
        for c in walk(v, "videoId"):
            vid = c; break
        out.append({"id": vid, "title": title, "views_txt": vtxt, "views": views_num(vtxt)})
    return out

def fmt_of(title, fm):
    t = title.lower()
    for name, keys in fm.items():
        if any(k in t for k in keys): return name
    return "other"

def collect():
    hist = json.load(open(HIST)) if os.path.exists(HIST) else []
    snap = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "yt": yt_shorts()}
    hist.append(snap)
    json.dump(hist, open(HIST, "w"), indent=1, ensure_ascii=False)
    print(f"collected {len(snap['yt'])} YT shorts")
    return hist

def report(min_age=24):
    hist = json.load(open(HIST))
    fm = json.load(open(FMT))["keywords"]
    fsp = os.path.join(G, "first_seen.json")   # id -> ISO time first seen (upload-time proxy; seed by hand)
    fs = json.load(open(fsp)) if os.path.exists(fsp) else {}
    now = datetime.datetime.now()
    last = hist[-1]["yt"]
    for v in last: fs.setdefault(v["id"], hist[-1]["ts"])
    json.dump(fs, open(fsp, "w"), indent=1)
    prev = {v["id"]: v["views"] for v in hist[-2]["yt"]} if len(hist) > 1 else {}
    age = {v["id"]: (now - datetime.datetime.fromisoformat(fs[v["id"]])).total_seconds() / 3600 for v in last}
    mature = [v for v in last if age[v["id"]] >= min_age]
    med = sorted(v["views"] for v in mature)[len(mature) // 2] if mature else 0
    print(f"YT shorts: {len(last)} ({len(mature)} older than {min_age}h) | median views of mature: {med}")
    agg = {}
    for v in sorted(last, key=lambda v: -v["views"]):
        f = fmt_of(v["title"], fm)
        a = age[v["id"]]
        gain = v["views"] - prev.get(v["id"], v["views"])
        if a < min_age:
            tag = "new"
        else:
            agg.setdefault(f, []).append(v["views"])
            tag = "WINNER" if med and v["views"] >= med else ("dead" if v["views"] < med / 10 else "")
        print(f"{v['views']:>7} (+{gain:<4}) {a:5.0f}h {v['views'] / max(a, 1):6.1f}/h {tag:6} [{f}] {v['title'][:60]}")
    vp = os.path.join(G, "voices.json")
    vm = json.load(open(vp)) if os.path.exists(vp) else {}
    # map queued files -> yt ids via post_queue links
    try:
        q = json.load(open(os.path.join(ROOT, "videos", "post_queue.json"), encoding="utf-8"))
        for e in q:
            fn = os.path.basename(e["file"].replace("\\", "/"))
            m = re.search(r"shorts/([\w-]{11})", str(e.get("status", {}).get("yt", "")))
            if m and fn in vm.get("files", {}): vm[m.group(1)] = vm["files"][fn]
    except Exception:
        pass
    vag = {}
    for v in last:
        if age[v["id"]] >= min_age and v["id"] in vm: vag.setdefault(vm[v["id"]], []).append(v["views"])
    if vag:
        print("\nBy voice (mature videos only, A/B test):")
        for k, vs in sorted(vag.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
            print(f"  {k:10} avg {sum(vs)/len(vs):7.0f}  median {sorted(vs)[len(vs)//2]:6}  n={len(vs)}")
    vph = {}
    for v in last:
        if age[v["id"]] >= 6:
            vph.setdefault(fmt_of(v["title"], fm), []).append(v["views"] / max(age[v["id"]], 1))
    print("\nBy format, views per hour (all videos 6h+, fair for young ones):")
    for f, vs in sorted(vph.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print(f"  {f:20} {sum(vs) / len(vs):7.1f}/h  n={len(vs)}")
    print("\nBy format (mature videos only):")
    for f, vs in sorted(agg.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        avg = sum(vs) / len(vs)
        verdict = "SCALE (make variations)" if avg >= med else ("KILL" if avg < med / 10 else "keep testing")
        print(f"  {f:20} avg {avg:7.0f}  n={len(vs)}  -> {verdict}")

if __name__ == "__main__":
    a = sys.argv[1:] or ["collect", "report"]
    if "collect" in a: collect()
    if "report" in a:
        ma = [int(x.split("=")[1]) for x in a if x.startswith("--min-age=")]
        report(ma[0] if ma else 24)
