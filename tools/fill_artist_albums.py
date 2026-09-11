import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
UA = "RateYourHipHop/1.0"
SKIP_TITLE = re.compile(
    r"greatest hits|the hits|playlist|karaoke|instrumental|acapella|"
    r"live at|live from|live in|come alive|"
    r"remix(es)?|anniversary|deluxe|collectors?|"
    r"extended version|expanded|remaster|soundtrack|inspired by|"
    r"compilation|best of|collection\b|mixtape volume|"
    r"bonus edition|alternate version|preluxe|chopped|"
    r"\bbeats\b|ringtones?|refill|curtain call|"
    r"edited version|explicit version|explicit booklet|"
    r"int'?l version|international version|"
    r"beginner's guide|back to the roots",
    re.I,
)
NON_GENRES = {
    85, 98, 106, 113, 129, 132, 169, 173, 466, 2,
}


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize(text: str) -> str:
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_albums():
    raw = (BASE / "js" / "albums.js").read_text(encoding="utf-8")
    raw = raw.replace("const albums =", "", 1).strip()
    if raw.endswith(";"):
        raw = raw[:-1]
    return json.loads(raw)


def split_artists(artist: str):
    return [part.strip() for part in re.split(r"\s+&\s+", artist) if part.strip()]


def search_artist_id(name: str):
    q = urllib.parse.quote(name)
    data = get_json(f"https://api.deezer.com/search/artist?q={q}&limit=8")
    wanted = normalize(name)
    best = None
    best_score = -1
    for item in data.get("data") or []:
        got = normalize(item.get("name") or "")
        if got == wanted:
            return item.get("id")
        if wanted in got or got in wanted:
            score = 80
        else:
            wa, wb = set(wanted.split()), set(got.split())
            score = int(100 * len(wa & wb) / max(len(wa), 1))
        fans = item.get("nb_fan") or 0
        score = score + min(fans / 1_000_000, 15)
        if score > best_score:
            best_score = score
            best = item
    if best and best_score >= 55:
        return best.get("id")
    return None


def artist_albums(artist_id: int):
    url = f"https://api.deezer.com/artist/{artist_id}/albums?limit=50"
    seen = []
    while url:
        data = get_json(url)
        seen.extend(data.get("data") or [])
        url = (data.get("next") or "").replace("http://", "https://")
        time.sleep(0.2)
        if len(seen) > 120:
            break
    return seen


def album_tracks(album_id: int):
    songs = []
    url = f"https://api.deezer.com/album/{album_id}/tracks?limit=100"
    while url:
        data = get_json(url)
        for track in data.get("data") or []:
            title = (track.get("title") or "").strip()
            if title:
                songs.append(title)
        url = (data.get("next") or "").replace("http://", "https://")
        time.sleep(0.12)
    return songs


def core_title(title: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", title or "")
    text = re.sub(r"\[[^\]]*\]", " ", text)
    return normalize(text)


def should_skip_title(title: str) -> bool:
    if SKIP_TITLE.search(title or ""):
        return True
    lowered = title.lower()
    if lowered.endswith(" ep"):
        return True
    if " edition" in lowered or " version" in lowered:
        return True
    return False


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    albums = load_albums()
    max_id = max(album["id"] for album in albums)
    existing_titles = {normalize(album["title"]) for album in albums}
    existing_cores = {core_title(album["title"]) for album in albums}
    existing_pairs = {
        (normalize(album["title"]), normalize(album["artist"]))
        for album in albums
    }

    artists = []
    seen_artists = set()
    for album in albums:
        for name in split_artists(album["artist"]):
            key = normalize(name)
            if key and key not in seen_artists:
                seen_artists.add(key)
                artists.append(name)

    print(f"Catalog: {len(albums)} albums, {len(artists)} artists")
    added = []

    for index, name in enumerate(artists, start=1):
        print(f"[{index}/{len(artists)}] {name}")
        try:
            artist_id = search_artist_id(name)
        except Exception as error:
            print("  search failed:", error)
            time.sleep(0.4)
            continue
        if not artist_id:
            print("  no Deezer artist")
            continue
        time.sleep(0.2)
        try:
            releases = artist_albums(artist_id)
        except Exception as error:
            print("  albums failed:", error)
            continue

        picked = []
        for release in releases:
            title = (release.get("title") or "").strip()
            record_type = (release.get("record_type") or "").lower()
            tracks_n = release.get("nb_tracks") or 0
            genre_id = release.get("genre_id")
            release_artist = ((release.get("artist") or {}).get("name") or "")
            if record_type not in {"album", ""}:
                continue
            if tracks_n and (tracks_n < 7 or tracks_n > 32):
                continue
            if genre_id in NON_GENRES:
                continue
            rel_norm = normalize(release_artist)
            name_norm = normalize(name)
            if rel_norm and name_norm not in rel_norm and rel_norm not in name_norm:
                continue
            if should_skip_title(title):
                continue
            key = normalize(title)
            core = core_title(title)
            if key in existing_titles or core in existing_cores:
                continue
            if (key, normalize(name)) in existing_pairs:
                continue
            date = release.get("release_date") or ""
            year = int(date[:4]) if date[:4].isdigit() else 0
            if year and year < 1985:
                continue
            picked.append(release)

        # Drop near-duplicate titles (deluxe already filtered)
        unique = []
        used = set()
        for release in picked:
            key = normalize(release.get("title") or "")
            core = core_title(release.get("title") or "")
            if key in used or key in existing_titles or core in existing_cores:
                continue
            used.add(key)
            unique.append(release)

        for release in unique:
            title = (release.get("title") or "").strip()
            album_id = release.get("id")
            date = release.get("release_date") or ""
            year = int(date[:4]) if date[:4].isdigit() else 0
            cover = (
                release.get("cover_xl")
                or release.get("cover_big")
                or release.get("cover")
                or ""
            )
            try:
                songs = album_tracks(album_id)
            except Exception as error:
                print("  tracks failed", title, error)
                continue
            if len(songs) < 7 or len(songs) > 32:
                continue
            max_id += 1
            entry = {
                "id": max_id,
                "title": title,
                "artist": name,
                "year": year or 0,
                "genre": "Hip-Hop",
                "cover": cover,
                "songs": songs,
            }
            albums.append(entry)
            added.append(f"{name} — {title} ({year})")
            existing_titles.add(normalize(title))
            existing_cores.add(core_title(title))
            existing_pairs.add((normalize(title), normalize(name)))
            print(f"  + {title} ({year}, {len(songs)} tracks)", flush=True)
            time.sleep(0.15)

        time.sleep(0.25)

    (BASE / "js" / "albums.js").write_text(
        "const albums = " + json.dumps(albums, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"\nAdded {len(added)} albums. Total now {len(albums)}.")
    for line in added:
        print(" ", line)


if __name__ == "__main__":
    main()
