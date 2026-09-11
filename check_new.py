import json
from pathlib import Path

d = json.loads(Path("album_fetch.json").read_text(encoding="utf-8"))
print("NEW MATCH QUALITY")
for x in d["new"]:
    it = (x.get("itunesTitle") or "").lower()
    t = x["title"].lower()
    if t.split()[0] not in it and it[:10] not in t:
        print(f"CHECK {x['score']:.0f} {x['title']} => {x.get('itunesTitle')} / {x.get('itunesArtist')} n={len(x.get('songs') or [])}")
