"""uploader.py - post a Short to YouTube / TikTok / Instagram via the user's logged-in Chrome.
Usage: python uploader.py <platform: yt|tt|ig> <video path> <title> <description/caption>
Prints a RESULT line. Relies on chrome.sh + studio.ps1 (screen 1920x1080, Chrome maximized).
"""
import json, os, re, subprocess, sys, time

T = "./tools/"
PS = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./tools/studio.ps1"
BASH = "./hermes/tools/git-2.53.0+3-win32-x64/usr/bin/bash.exe"
VIEW_Y = 112  # legacy
DPR = 1.25    # Windows display scaling (125%)
PAGE_Y = 106  # screen y of page top


def sh(c, t=180):
    r = subprocess.run([BASH, "-c", c], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True,
                       timeout=t, encoding="utf-8", errors="replace")
    return (r.stdout + r.stderr).replace(" - Google Chrome", "").strip()


def js(code, wait=2):
    open(T + "js_tmp.txt", "w", encoding="utf-8").write(code)
    return sh(f"bash chrome.sh js js_tmp.txt {wait}; bash chrome.sh title")


def click(x, y):
    sh(f"{PS} -action cfront >/dev/null; {PS} -action rawclick -x {int(x)} -y {int(y)} >/dev/null")


def keys(k):
    sh(f"{PS} -action rawkeys -keys '{k}' >/dev/null")


def pick(path):
    # keyboard-only: works wherever the Open dialog appears
    time.sleep(3.5)
    keys("%n"); time.sleep(0.4)
    keys("^a")
    sh(f"{PS} -action paste -text '{path}' >/dev/null")
    time.sleep(0.8)
    keys("{ENTER}")


def paste_text(text):
    open(T + "clip.txt", "w", encoding="utf-8").write(text)
    sh("powershell.exe -NoProfile -Command \"Set-Clipboard -Value (Get-Content -Raw -Encoding UTF8 './tools\\clip.txt')\"")
    keys("^v")


def yt(path, title, desc):
    sh('bash chrome.sh go "https://www.youtube.com/upload" 9')
    click(958, 694)  # Select files
    pick(path)
    time.sleep(10)
    put = ("function put(el,s){el.focus();document.execCommand('selectAll',false,null);document.execCommand('insertText',false,s);}")
    o = js("javascript:(function(){" + put + "var t=document.querySelectorAll('#textbox');"
           f"if(t.length>=2){{put(t[0],{json.dumps(title)});put(t[1],{json.dumps(desc)});}}"
           "var r=document.querySelector('tp-yt-paper-radio-button[name=\"VIDEO_MADE_FOR_KIDS_NOT_MFK\"]');if(r){r.click();}"
           "document.title='META '+t.length+' kids='+(!!r);})()", 3)
    for _ in range(3):
        sh("bash chrome.sh js js_yt_next.txt 3")
    o += " | " + sh("bash chrome.sh js js_yt_public.txt 2; bash chrome.sh title")
    o += " | " + sh("bash chrome.sh js js_yt_done.txt 8; bash chrome.sh title")
    l = sh("bash chrome.sh js js_yt_link.txt 2; bash chrome.sh title")
    return o + " | " + l


def tt(path, title, caption):
    # make sure the upload page really loaded (Oct 7: another job's Chrome navigation left us on a Roblox page)
    for _ in range(3):
        sh('bash chrome.sh go "https://www.tiktok.com/tiktokstudio/upload" 12')
        t = js("javascript:(function(){document.title='URL '+location.pathname+' sel='+!![...document.querySelectorAll('button')].find(function(x){return /Select video/i.test(x.innerText)});})()", 1)
        if "tiktokstudio/upload" in t and "sel=true" in t:
            break
        time.sleep(8)
    # clear a leftover-draft banner (it shifts the layout and breaks the flow)
    d = js("javascript:(function(){var b=[...document.querySelectorAll('button')].find(function(x){return x.innerText.trim()==='Discard'});"
           "if(b){b.click();setTimeout(function(){var c=[...document.querySelectorAll('button')].filter(function(x){return x.innerText.trim()==='Discard'}).pop();if(c)c.click();},800);}"
           "document.title='DRAFT '+(!!b);})()", 3)
    if "true" in d:
        sh('bash chrome.sh go "https://www.tiktok.com/tiktokstudio/upload" 10')
    # select video button (centre of upload card)
    o = js("javascript:(function(){var b=[...document.querySelectorAll('button')].find(function(x){return /Select video/i.test(x.innerText)});"
           "if(b){var r=b.getBoundingClientRect();document.title='SEL '+Math.round(r.x+r.width/2)+','+Math.round(r.y+r.height/2);}else document.title='SEL none';})()")
    try:
        x, y = o.split("SEL ")[1].split()[0].split(",")
        click(int(x), int(y) + VIEW_Y)
    except Exception:
        click(1114, 666)
    pick(path)
    time.sleep(14)
    # close any 'turn on automatic content checks' popup
    js("javascript:(function(){var b=[...document.querySelectorAll('button')].find(function(x){return /^(Turn on|Got it|OK)$/i.test(x.innerText.trim())});if(b)b.click();document.title='POP '+(!!b);})()")
    for _ in range(14):  # wait for upload to finish
        st = js(open(T + "js_tt_state.txt").read().strip(), 1)
        if "post=true" in st and "Uploaded" in st:
            break
        time.sleep(5)
    snd = ""
    if os.environ.get("TT_SOUND"):
        snd = " | " + tt_add_sound(os.environ["TT_SOUND"], int(os.environ.get("TT_SOUND_DB", "-12")))
        if "no Sounds button" in snd:   # editor not ready yet: wait and try once more
            time.sleep(15)
            snd = " | " + tt_add_sound(os.environ["TT_SOUND"], int(os.environ.get("TT_SOUND_DB", "-12")))
        time.sleep(4)
    # caption: REAL click + paste. JS execCommand insertText crashes TikTok Studio ("Something went wrong") - Oct 6 2026
    r = js("javascript:(function(){var e=document.querySelector('.public-DraftEditor-content,[contenteditable=true]');if(!e){document.title='ED none';return;}"
           "e.scrollIntoView({block:'center'});var r=e.getBoundingClientRect();document.title='ED '+Math.round(r.x+40)+','+Math.round(r.y+15);})()", 2)
    try:
        ex, ey = r.split("ED ")[1].split()[0].split(",")
        click(int(ex) * DPR, int(ey) * DPR + PAGE_Y)
    except Exception:
        click(560, 560)
    time.sleep(0.6); keys("^a"); time.sleep(0.3); keys("{BACKSPACE}"); time.sleep(0.5)
    paste_text(caption); time.sleep(2)
    keys("{ESC}"); time.sleep(0.5)
    click(1300, 420); time.sleep(1)  # blank spot: closes hashtag suggestions
    c = js("javascript:(function(){var e=document.querySelector('.public-DraftEditor-content,[contenteditable=true]');document.title='CAP '+(e?e.innerText.length:-1)+' wrong='+(document.body.innerText.indexOf('Something went wrong')>=0);})()", 1)
    return st + snd + " | " + c + " | " + sh("bash chrome.sh js js_tt_post2.txt 10; bash chrome.sh title")


def tt_add_sound(query, vol_db=-12):
    """Open TikTok Studio editor -> Sounds, search `query`, add first result, lower its volume, Save."""
    o = js("javascript:(function(){var b=[...document.querySelectorAll('button,div[role=button],span')].find(function(x){return (x.innerText||'').trim()==='Sounds'});"
           "if(!b){document.title='SND none';return;}b.scrollIntoView({block:'center'});setTimeout(function(){var r=b.getBoundingClientRect();"
           "document.title='SND '+Math.round(r.x+r.width/2)+','+Math.round(r.y+r.height/2);},500);})()", 2)
    try:
        x, y = o.split("SND ")[1].split()[0].split(",")
    except Exception:
        return "no Sounds button"
    click(int(x) * DPR, int(y) * DPR + PAGE_Y); time.sleep(7)
    click(618, 652); time.sleep(1)        # 'Got it' on phone-mode tip (harmless)
    click(300, 292); keys("^a")
    sh(f"{PS} -action paste -text '{query}' >/dev/null"); keys("{ENTER}"); time.sleep(5)
    idx = int(os.environ.get("TT_SOUND_IDX", "0"))
    name = js("javascript:(function(){var it=[...document.querySelectorAll('div,li')].filter(function(e){var t=e.innerText||'';return /\\d\\d:\\d\\d/.test(t)&&t.length<120&&e.getBoundingClientRect().x<520&&e.getBoundingClientRect().height>40&&e.getBoundingClientRect().height<110;});"
              "var seen={},names=[];it.forEach(function(e){var n=e.innerText.split('\\n')[0];if(!seen[n]){seen[n]=1;names.push(n);}});document.title='SNDS '+names.slice(0,6).join(' || ');})()", 1)
    click(484, 368 + 80 * idx); time.sleep(4)   # + on result #idx (rows are 80px apart)
    # set added-sound volume via the Audio panel number box
    click(1724, 340); keys("^a")
    sh(f"{PS} -action paste -text '{vol_db}' >/dev/null"); keys("{ENTER}"); time.sleep(1)
    click(1838, 150); time.sleep(6)       # Save (editor top-right)
    try:
        nm = name.split("SNDS ")[1].replace(" - Google Chrome", "").split(" || ")[idx]
    except Exception:
        nm = "?"
    return f"sound added: {query}#{idx} = {nm}"


def ig(path, title, caption):
    # fixed coordinates (1920x1080, Chrome maximized) - proven flow
    sh('bash chrome.sh go "https://www.instagram.com/" 8')
    # + Create: find the sidebar icon by its label (IG moves the sidebar items around; Oct 12 it moved 664 -> 630).
    # Windows display scale is 125%: screen px = (Chrome UI height + CSS y) * devicePixelRatio (Chrome is maximized at y=0).
    r = js("javascript:(function(){var s=document.querySelector('svg[aria-label=\"New post\"],svg[aria-label=\"Create\"]');"
           "if(!s){document.title='CR none';return;}var b=s.getBoundingClientRect(),d=window.devicePixelRatio,ui=window.outerHeight-window.innerHeight;"
           "document.title='CR '+Math.round((b.left+b.width/2)*d)+' '+Math.round((ui+b.top+b.height/2)*d);})()", 1)
    m = re.search(r"CR (\d+) (\d+)", r or "")
    cx, cy = (int(m.group(1)), int(m.group(2))) if m else (44, 630)
    click(cx, cy); time.sleep(2.5)       # + Create
    # Oct 12: Create now opens a small menu (Post / Live video / Ad) -> click "Post" if that menu is there
    r = js("javascript:(function(){var d=window.devicePixelRatio,ui=window.outerHeight-window.innerHeight,hit=null;"
           "document.querySelectorAll('span,div').forEach(function(e){if(!hit&&e.childElementCount==0&&e.textContent.trim()=='Post'){"
           "var b=e.getBoundingClientRect();if(b.width>0&&b.left<400)hit=b;}});"
           "document.title=hit?'PM '+Math.round((hit.left+hit.width/2)*d)+' '+Math.round((ui+hit.top+hit.height/2)*d):'PM none';})()", 1)
    m = re.search(r"PM (\d+) (\d+)", r or "")
    if m:
        click(int(m.group(1)), int(m.group(2))); time.sleep(2.5)
    click(950, 674)                      # Select from computer
    pick(path); time.sleep(7)
    click(950, 764); time.sleep(2)       # OK on 'video posts are now reels' (harmless if absent)
    click(672, 870); time.sleep(1.5)     # crop icon
    click(700, 620); time.sleep(1.5)     # Original
    click(1230, 246); time.sleep(3)      # Next (crop)
    click(1440, 246); time.sleep(3)      # Next on edit step (dialog widens) -> caption step
    st = js("javascript:(function(){var t=document.body.innerText;document.title='CAPBOX '+/Add a caption|Write a caption/.test(t);})()", 1)
    if "true" not in st:
        return "IG caption box not found: " + st
    click(1260, 400)
    paste_text(caption); time.sleep(1.5)
    sh(f"{PS} -action shot >/dev/null; cp $LOCALAPPDATA/hermes/cache/scratch/screen.png ../videos/ig_precheck.png")
    click(1438, 246)  # Share
    r = ""
    for _ in range(24):
        time.sleep(5)
        r = js("javascript:(function(){var t=document.body.innerText;var m=t.match(/(Your reel has been shared|Reel shared|Your post has been shared|Something went wrong)/);document.title='IG '+(m?m[0]:'?');})()", 1)
        if "shared" in r.lower() or "wrong" in r.lower():
            break
    keys("{ESC}")
    return r


if __name__ == "__main__":
    plat, path, title, desc = sys.argv[1:5]
    fn = {"yt": yt, "tt": tt, "ig": ig}[plat]
    try:
        print("RESULT", plat, path.split("\\")[-1], "::", fn(path, title, desc), flush=True)
    except Exception as e:
        print("RESULT", plat, path.split("\\")[-1], ":: ERROR", e, flush=True)
