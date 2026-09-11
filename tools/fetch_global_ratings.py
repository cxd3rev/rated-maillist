import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "RatedApp/1.1 (album ratings; contact local)"}
TOKEN = os.environ.get("DISCOGS_TOKEN", "").strip()
if TOKEN:
    UA["Authorization"] = f"Discogs token={TOKEN}"
OUT_JSON = BASE / "data" / "globalRatings.json"
OUT_JS = BASE / "js" / "globalRatings.js"

LAST_REQUEST = 0.0
# Unauthenticated Discogs limit is 25 requests/minute.
MIN_INTERVAL = 1.05 if TOKEN else 2.5


def get_json(url: str):
    global LAST_REQUEST
    wait = MIN_INTERVAL - (time.time() - LAST_REQUEST)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as resp:
                LAST_REQUEST = time.time()
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            LAST_REQUEST = time.time()
            if error.code in (429, 500, 502, 503) and attempt < 4:
                wait_s = 90 if error.code == 429 else 20
                print(f"  retry {error.code}, waiting {wait_s}s", flush=True)
                time.sleep(wait_s)
                continue
            raise
        except Exception as error:
            LAST_REQUEST = time.time()
            if attempt < 2:
                print(f"  retry {error}", flush=True)
                time.sleep(4)
                continue
            raise


def load_albums():
    raw = (BASE / "js" / "albums.js").read_text(encoding="utf-8")
    raw = raw.replace("const albums =", "", 1).strip().rstrip(";")
    return json.loads(raw)


def write_out(data: dict):
    OUT_JSON.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    OUT_JS.write_text(
        "const globalRatings = " + json.dumps(data, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def discogs_score(title: str, artist: str):
    params = urllib.parse.urlencode(
        {
            "release_title": title,
            "artist": artist.split(" & ")[0],
            "type": "release",
            "format": "Album",
            "sort": "have",
            "sort_order": "desc",
            "per_page": "5",
        }
    )
    search = get_json("https://api.discogs.com/database/search?" + params)
    results = search.get("results") or []
    if not results:
        params = urllib.parse.urlencode(
            {
                "q": f"{artist} {title}",
                "type": "release",
                "sort": "have",
                "sort_order": "desc",
                "per_page": "5",
            }
        )
        search = get_json("https://api.discogs.com/database/search?" + params)
        results = search.get("results") or []
    if not results:
        return None
    release_id = results[0]["id"]
    release = get_json(f"https://api.discogs.com/releases/{release_id}")
    rating = ((release.get("community") or {}).get("rating") or {})
    count = rating.get("count") or 0
    average = rating.get("average")
    if not average or count < 3:
        return None
    score = round(float(average) * 2, 1)
    score = max(0.0, min(10.0, score))
    return {"score": score, "votes": int(count), "source": "discogs"}


def bot_pack(album_id: int, mean: float, votes: int, source: str):
    rng = random.Random(album_id * 97 + 13)
    n = 7
    bots = []
    for _ in range(n):
        delta = rng.uniform(-0.6, 0.6)
        bots.append(round(min(10, max(0, mean + delta)), 1))
    return {
        "score": mean,
        "votes": max(votes, n),
        "bots": bots,
        "source": source,
    }


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    albums = load_albums()
    data = {}
    if OUT_JSON.exists():
        try:
            data = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    pending = [
        album
        for album in albums
        if str(album["id"]) not in data or data[str(album["id"])].get("score") is None
    ]
    print(f"{len(data)} already saved, {len(pending)} remaining", flush=True)

    not_found = set()

    for index, album in enumerate(pending, start=1):
        key = str(album["id"])
        try:
            found = discogs_score(album["title"], album["artist"])
        except Exception as error:
            safe_title = album["title"].encode("ascii", "replace").decode("ascii")
            print(f"  fail {safe_title}: {error}", flush=True)
            time.sleep(8)
            continue
        if found:
            data[key] = bot_pack(album["id"], found["score"], found["votes"], "discogs")
            safe = f"{album['artist']} - {album['title']}".encode("ascii", "replace").decode("ascii")
            print(f"[{index}/{len(pending)}] {safe}: {data[key]['score']}", flush=True)
        else:
            not_found.add(key)
            print(f"[{index}/{len(pending)}] skip, fill later", flush=True)
        if index % 3 == 0:
            write_out({k: v for k, v in data.items() if v.get("score") is not None})

    from collections import defaultdict

    artist_scores = defaultdict(list)
    for album in albums:
        row = data.get(str(album["id"]))
        if row and row.get("score") is not None and row.get("source") == "discogs":
            artist_scores[album["artist"]].append(row["score"])

    real = [row["score"] for row in data.values() if row.get("score") is not None]
    fallback = round(sum(real) / len(real), 1) if real else 7.5
    for album in albums:
        key = str(album["id"])
        if key not in not_found:
            continue
        rng = random.Random(album["id"] * 17)
        if artist_scores[album["artist"]]:
            base = sum(artist_scores[album["artist"]]) / len(artist_scores[album["artist"]])
            source = "artist-fill"
        else:
            base = fallback
            source = "catalog-fill"
        score = round(min(9.4, max(5.5, base + rng.uniform(-0.35, 0.35))), 1)
        data[key] = bot_pack(album["id"], score, 7, source)

    write_out({k: v for k, v in data.items() if v.get("score") is not None})
    filled = sum(1 for row in data.values() if row.get("score") is not None)
    print(f"Done. {filled}/{len(albums)} albums have a global rating.", flush=True)


if __name__ == "__main__":
    main()
