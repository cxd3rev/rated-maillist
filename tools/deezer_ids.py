import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "RateYourHipHop/1.0"
IDS = {
    "Cheat Codes": 1052448642,
    "Take Care": 1622724,
    "Cruel Summer": 5943677,
    "PRhyme": 8865939,
    "Fetty Wap": 54266702,
    "Eve": 107878202,
    "Glorious Game": 385949677,
    "Run the Jewels": 882538842,
    "Under Pressure": 8844411,
    "Honest": 7707620,
    "Psychodrama": 820326491,
    "Miles": 146853022,
    "Drill Music in Zion": 329619147,
    "SCARING THE HOES": 415190837,
    "Samurai": 575083101,
    "HOME?": 725011061,
}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tracks(album_id):
    songs = []
    url = f"https://api.deezer.com/album/{album_id}/tracks?limit=100"
    while url:
        data = get_json(url)
        for t in data.get("data") or []:
            if t.get("title"):
                songs.append(t["title"])
        url = data.get("next")
        time.sleep(0.1)
    return songs


out = {}
for title, aid in IDS.items():
    print(title, aid)
    alb = get_json(f"https://api.deezer.com/album/{aid}")
    songs = tracks(aid)
    out[title] = {
        "deezerTitle": alb.get("title"),
        "deezerArtist": (alb.get("artist") or {}).get("name"),
        "cover": alb.get("cover_xl") or alb.get("cover_big"),
        "songs": songs,
        "year": int((alb.get("release_date") or "0")[:4] or 0),
    }
    print(" ", alb.get("title"), len(songs))
    time.sleep(0.15)

(ROOT / "data" / "deezer_ids.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("wrote deezer_ids.json")
