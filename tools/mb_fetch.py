import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RateYourHipHop/1.0 (student project; local app)"
DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "album_fetch.json").read_text(encoding="utf-8"))


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize(text: str) -> str:
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def similar(a: str, b: str) -> float:
    a, b = set(normalize(a).split()), set(normalize(b).split())
    if not a:
        return 0
    return len(a & b) / len(a)


def mb_search(title: str, artist: str):
    query = f'release:"{title}" AND artist:"{artist}" AND primarytype:album'
    url = "https://musicbrainz.org/ws/2/release-group/?query=" + urllib.parse.quote(query) + "&fmt=json&limit=8"
    time.sleep(1.1)
    data = get_json(url)
    groups = data.get("release-groups") or []
    if not groups:
        query = f"{title} AND artist:{artist}"
        url = "https://musicbrainz.org/ws/2/release-group/?query=" + urllib.parse.quote(query) + "&fmt=json&limit=8"
        time.sleep(1.1)
        data = get_json(url)
        groups = data.get("release-groups") or []
    best = None
    best_score = 0
    for g in groups:
        cred = ", ".join(x.get("name", "") for x in g.get("artist-credit") or [])
        score = similar(title, g.get("title", "")) * 2 + similar(artist, cred)
        if score > best_score:
            best_score = score
            best = g
    if not best or best_score < 0.8:
        return None
    return best


def mb_cover(mbid: str) -> str:
    url = f"https://coverartarchive.org/release-group/{mbid}"
    time.sleep(1.1)
    try:
        data = get_json(url)
    except Exception:
        return ""
    for img in data.get("images") or []:
        if img.get("front") or "Front" in (img.get("types") or []):
            thumbs = img.get("thumbnails") or {}
            return thumbs.get("500") or thumbs.get("large") or img.get("image") or ""
    if data.get("images"):
        img = data["images"][0]
        thumbs = img.get("thumbnails") or {}
        return thumbs.get("500") or img.get("image") or ""
    return ""


def mb_songs(mbid: str):
    time.sleep(1.1)
    group = get_json(
        f"https://musicbrainz.org/ws/2/release-group/{mbid}?inc=releases&fmt=json"
    )
    releases = group.get("releases") or []
    if not releases:
        return []
    official = [r for r in releases if r.get("status") == "Official"] or releases
    rid = official[0]["id"]
    time.sleep(1.1)
    rel = get_json(
        f"https://musicbrainz.org/ws/2/release/{rid}?inc=recordings&fmt=json"
    )
    songs = []
    for medium in rel.get("media") or []:
        for track in medium.get("tracks") or []:
            rec = track.get("recording") or {}
            name = rec.get("title") or track.get("title")
            if name:
                songs.append(name)
    return songs


def main():
    retry = []
    seen = set()
    for m in DATA["missing"]:
        key = (m["title"], m["artist"], m["year"])
        if key not in seen:
            retry.append(m)
            seen.add(key)
    for x in DATA["existing"]:
        if x.get("score", 0) < 140 or len(x.get("songs") or []) < 5:
            key = (x["title"], x["artist"], x["year"])
            if key not in seen:
                retry.append(
                    {
                        "kind": "existing",
                        "title": x["title"],
                        "artist": x["artist"],
                        "year": x["year"],
                    }
                )
                seen.add(key)

    found = []
    still = []
    for i, item in enumerate(retry, 1):
        title, artist, year = item["title"], item["artist"], item["year"]
        print(f"[{i}/{len(retry)}] {artist} - {title}")
        try:
            group = mb_search(title, artist)
            if not group:
                still.append(item)
                print("  no group")
                continue
            cover = mb_cover(group["id"])
            songs = mb_songs(group["id"])
            if not cover:
                still.append(item)
                print("  no cover")
                continue
            rec = {
                "kind": item.get("kind", "new"),
                "title": title,
                "artist": artist,
                "year": year,
                "cover": cover,
                "songs": songs,
                "source": "musicbrainz",
                "mbTitle": group.get("title"),
            }
            found.append(rec)
            print(f"  ok cover songs={len(songs)}")
        except Exception as exc:
            item["error"] = str(exc)
            still.append(item)
            print("  err", exc)

    (Path(__file__).resolve().parent.parent / "data" / "album_retry.json").write_text(
        json.dumps({"found": found, "still": still}, indent=2),
        encoding="utf-8",
    )
    print("found", len(found), "still", len(still))


if __name__ == "__main__":
    main()
