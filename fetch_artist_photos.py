import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RateYourHipHop/1.0"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def split_names(artist):
    return [part.strip() for part in artist.split(" & ") if part.strip()]


def search_artist(name):
    url = "https://api.deezer.com/search/artist?q=" + urllib.parse.quote(name) + "&limit=8"
    data = get_json(url)
    wanted = name.lower().replace(".", "").replace("$", "s")
    best = None
    for artist in data.get("data") or []:
        got = (artist.get("name") or "").lower().replace(".", "").replace("$", "s")
        picture = artist.get("picture_xl") or artist.get("picture_big") or artist.get("picture_medium")
        if not picture:
            continue
        if got == wanted:
            return picture
        if wanted in got or got in wanted:
            best = best or picture
    if best:
        return best
    first = (data.get("data") or [None])[0]
    if first:
        return first.get("picture_xl") or first.get("picture_big") or first.get("picture_medium")
    return ""


albums = json.loads(Path("albums.js").read_text(encoding="utf-8").split("=", 1)[1].strip()[:-1])
names = []
seen = set()
for album in albums:
    for name in split_names(album["artist"]):
        if name not in seen:
            seen.add(name)
            names.append(name)

photos = {}
missing = []
print("artists", len(names))
for index, name in enumerate(names, 1):
    try:
        photo = search_artist(name)
    except Exception as error:
        print("ERR", name, error)
        photo = ""
        time.sleep(0.4)
    if photo:
        photos[name] = photo
        print(index, "ok", name)
    else:
        missing.append(name)
        print(index, "MISS", name)
    time.sleep(0.12)

Path("artistPhotos.js").write_text(
    "const artistPhotos = "
    + json.dumps(photos, ensure_ascii=False, separators=(",", ":"))
    + ";\n",
    encoding="utf-8",
)
print("saved", len(photos), "missing", missing)
