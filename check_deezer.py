import json
from pathlib import Path

d = json.loads(Path("deezer_albums.json").read_text(encoding="utf-8"))
print("MISSING")
for m in d["missing"]:
    print(m)

print("\nSHORT OR SUSPECT")
for x in d["found"]:
    n = len(x.get("songs") or [])
    dt = (x.get("deezerTitle") or "").lower()
    t = x["title"].lower()
    if n < 4 or "single" in dt:
        print(f"n={n} {x.get('displayArtist')} | {x['title']} => {x.get('deezerTitle')}")
    # HOME
    if x["title"] in {"HOME?", "Old", "IV", "XXX", "Miles", "Maps"}:
        print(f"CHECK {x.get('displayArtist')} {x['title']} => {x.get('deezerTitle')} / {x.get('deezerArtist')} n={n}")
