import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "deezer_albums.json").read_text(encoding="utf-8"))
want = ["Wolf", "Doris", "Piñata", "Pinata", "Shoot for the Stars Aim for the Moon", "Burning Desire"]
for x in d["found"]:
    if any(w.lower() in x["title"].lower() for w in ["wolf", "doris", "pi", "shoot", "burning"]):
        print(x["title"], "=>", x.get("deezerTitle"), x.get("deezerArtist"), "n=", len(x.get("songs") or []))
        if "Pi" in x["title"] or x["title"]=="Wolf" or x["title"]=="Doris":
            print("  first3", (x.get("songs") or [])[:3], "last3", (x.get("songs") or [])[-3:])
