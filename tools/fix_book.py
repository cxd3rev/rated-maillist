import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "js" / "albums.js"
albums = json.loads(path.read_text(encoding="utf-8").split("=", 1)[1].strip()[:-1])
albums.append(
    {
        "id": 133,
        "title": "Book of Ryan",
        "artist": "Royce da 5'9\"",
        "year": 2018,
        "genre": "Hip-Hop",
        "cover": "https://cdn-images.dzcdn.net/images/cover/0524d316efd6024acf8b90d3cd8efc5a/1000x1000-000000-80-0-0.jpg",
        "songs": [
            "Intro",
            "Woke",
            "My Parallel (Skit)",
            "Caterpillar (feat. Eminem & King Green)",
            "God Speed (feat. Ashley Sorrell)",
            "Dumb (feat. Boogie)",
            "Who Are You (Skit)",
            "Cocaine",
            "Life Is Fair",
            "Boblo Boat (feat. J. Cole)",
            "Legendary",
            "Summer On Lock (feat. Pusha T, Jadakiss, Fabolous & Agent Sasco",
            "Amazing (feat. Melanie Rutherford)",
            "Outside (feat. Marsha Ambrosius & Robert Glasper)",
            "Power",
            "Protecting Ryan (Skit)",
            "Strong Friend",
            "Anything/Everything",
            "Stay Woke (feat. Ashley Sorrell)",
            "First Of The Month (feat. T Pain & Chavis Chandler)",
            "Caterpillar Remix (feat. Logic & King Green)",
        ],
    }
)
albums.sort(key=lambda album: album["id"])
path.write_text(
    "const albums = "
    + json.dumps(albums, ensure_ascii=False, separators=(",", ":"))
    + ";\n",
    encoding="utf-8",
)
print(len(albums))
