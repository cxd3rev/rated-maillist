import json
from pathlib import Path
from collections import Counter

d = json.loads(Path("album_fetch.json").read_text(encoding="utf-8"))
c = Counter()
for m in d["missing"][:15]:
    r = m["result"]
    print(m["title"], "->", r)
    c[str(r.get("error") if isinstance(r, dict) else r)] += 1
print("...")
for m in d["missing"]:
    r = m["result"]
    if isinstance(r, dict):
        c[r.get("error", "other")] += 1
print(c)
print("new ok", len(d["new"]))
print("sample new", [x["title"] for x in d["new"][:20]])
