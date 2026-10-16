"""push_places.py - publish local .rbxlx builds to the live Roblox places via Open Cloud (no Studio).
Usage: python push_places.py [folder ...]   (default: all 5 games)
Key: tools/.rbx_api_key (universe-place-instances:write). Never printed.
"""
import subprocess, sys, urllib.request, urllib.error, json, os

R = "./"
KEY = open(R + "tools/.rbx_api_key", encoding="utf-8").read().strip()
GAMES = {  # folder: (rbxlx, universeId, placeId)
    "steal_a_pet": ("StealAPet.rbxlx", 10768497839, 104938688727960),
    "nights_forest": ("NightsForest.rbxlx", 10768498151, 118141248008355),
    "blade_ball": ("BladeBall.rbxlx", 10768498273, 120375526854160),
    "speed_escape": ("SpeedEscape.rbxlx", 10768498409, 114957991573074),
    "ride_a_pet": ("RideAPet.rbxlx", 10768498518, 131189886345972),
    # private test builds (owner-only); not in the default list
    "quiet_place": ("AQuietPlace.rbxlx", 10770002826, 113077276786587),
    "tilt": ("Tilt.rbxlx", 10770931107, 118492233399605),  # PRIVATE test upload Oct 15; public only on sir's "publish"
    "secret_game": ("EverybodyHasASecret.rbxlx", 10770003100, 78205601926730),
}
DEFAULT = ["steal_a_pet", "nights_forest", "blade_ball", "speed_escape", "ride_a_pet"]


def push(folder):
    f, u, p = GAMES[folder]
    b = subprocess.run([R + "tools/rojo.exe", "build", "default.project.json", "-o", f], cwd=R + folder,
                       capture_output=True, text=True)
    if b.returncode:
        return f"{folder}: BUILD FAIL {b.stderr[-300:]}"
    data = open(R + folder + "/" + f, "rb").read()
    req = urllib.request.Request(
        f"https://apis.roblox.com/universes/v1/{u}/places/{p}/versions?versionType=Published",
        data=data, method="POST",
        headers={"x-api-key": KEY, "Content-Type": "application/xml"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return f"{folder}: OK version {json.loads(r.read()).get('versionNumber')}"
    except urllib.error.HTTPError as e:
        return f"{folder}: HTTP {e.code} {e.read()[:300].decode(errors='replace')}"


if __name__ == "__main__":
    for g in (sys.argv[1:] or DEFAULT):
        print(push(g), flush=True)
