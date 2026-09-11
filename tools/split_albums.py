import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
source = root.joinpath("js", "script.js").read_text(encoding="utf-8")

marker = "/* =====================================================\n   API"
if marker not in source:
    raise SystemExit("Could not find API section in script.js")

data_part, app_part = source.split(marker, 1)

pattern = re.compile(
    r"id:\s*(\d+),\s*title:\s*\"([^\"]+)\",\s*artist:\s*\"([^\"]+)\",\s*year:\s*(\d+),\s*genre:\s*\"([^\"]+)\",\s*cover:\s*\"([^\"]+)\",\s*songs:\s*\[(.*?)\]",
    re.S,
)

albums = []
for match in pattern.finditer(data_part):
    albums.append(
        {
            "id": int(match.group(1)),
            "title": match.group(2),
            "artist": match.group(3),
            "year": int(match.group(4)),
            "genre": match.group(5),
            "cover": match.group(6),
            "songs": re.findall(r"\"([^\"]+)\"", match.group(7)),
        }
    )

if len(albums) < 50:
    raise SystemExit(f"Too few albums parsed: {len(albums)}")

albums_js = "const albums = " + json.dumps(albums, ensure_ascii=False, separators=(",", ":")) + ";\n"
root.joinpath("js", "albums.js").write_text(albums_js, encoding="utf-8")

app_js = marker + app_part
root.joinpath("js", "script.js").write_text(app_js, encoding="utf-8")

print("albums", len(albums), "albums.js bytes", len(albums_js.encode("utf-8")), "script.js bytes", len(app_js.encode("utf-8")))
