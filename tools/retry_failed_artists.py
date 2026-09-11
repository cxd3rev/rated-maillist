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
    r"compilation|best of|collection\b|"
    r"bonus edition|alternate version|preluxe|chopped|"
    r"\bbeats\b|ringtones?|refill|curtain call|"
    r"edited version|explicit version|explicit booklet|"
    r"int'?l version|international version|sped up|slowed|"
    r"bonus tracks|directors cut",
    re.I,
)
NON_GENRES = {85, 98, 106, 113, 129, 132, 169, 173, 466, 2}
MAX_ALBUMS_PER_ARTIST = 12

RETRY = [
    "Lil Wayne",
    "Lil Baby",
    "Cardi B",
    "King Von",
    "DMX",
    "Stormzy",
    "Homixide Gang",
    "Madvillain",
    "Method Man",
    "DaBaby",
    "Lil Tjay",
    "Kevin Gates",
    "Digga D",
    "Stove God Cooks",
    "Che",
    "Kashdami",
    "Young Nudy",
    "Lil B",
    "G Herbo",
    "Quando Rondo",
    "Pooh Shiesty",
    "EST Gee",
    "Babyface Ray",
    "Tee Grizzley",
    "A$AP Twelvyy",
]


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
    raw = raw.replace("const albums =", "", 1).strip().rstrip(";")
    return json.loads(raw)


def search_artist(name: str):
    q = urllib.parse.quote(name)
    data = get_json(f"https://api.deezer.com/search/artist?q={q}&limit=12")
    wanted = normalize(name)
    exact = []
    fuzzy = []
    for item in data.get("data") or []:
        got = normalize(item.get("name") or "")
        fans = item.get("nb_fan") or 0
        if got == wanted:
            exact.append((fans, item))
        else:
            wa, wb = set(wanted.split()), set(got.split())
            overlap = len(wa & wb)
            if wanted in got or got in wanted or overlap >= max(1, len(wa) - 0):
                fuzzy.append((fans + overlap * 1000, item))
    if exact:
        exact.sort(key=lambda x: x[0], reverse=True)
        item = exact[0][1]
        return item.get("id"), item.get("name") or name
    if fuzzy:
        fuzzy.sort(key=lambda x: x[0], reverse=True)
        item = fuzzy[0][1]
        if (item.get("nb_fan") or 0) >= 2000:
            return item.get("id"), item.get("name") or name
    return None, None


def artist_albums(artist_id: int):
    url = f"https://api.deezer.com/artist/{artist_id}/albums?limit=50"
    seen = []
    while url:
        data = get_json(url)
        seen.extend(data.get("data") or [])
        url = (data.get("next") or "").replace("http://", "https://")
        time.sleep(0.2)
        if len(seen) > 140:
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
    if " edition" in lowered or " version" in lowered:
        return True
    return False


def search_photo(name: str) -> str:
    _id, canon = search_artist(name)
    if not _id:
        return ""
    data = get_json(f"https://api.deezer.com/artist/{_id}")
    return data.get("picture_xl") or data.get("picture_big") or ""


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

    added = []
    found_artists = []
    for index, name in enumerate(RETRY, start=1):
        print(f"[{index}/{len(RETRY)}] {name}", flush=True)
        try:
            artist_id, canon = search_artist(name)
        except Exception as error:
            print("  search failed", error, flush=True)
            continue
        if not artist_id:
            print("  no Deezer artist", flush=True)
            continue
        display = canon or name
        print(f"  matched {display} id={artist_id}", flush=True)
        found_artists.append(display)
        time.sleep(0.15)
        try:
            releases = artist_albums(artist_id)
        except Exception as error:
            print("  albums failed", error, flush=True)
            continue

        picked = []
        for release in releases:
            title = (release.get("title") or "").strip()
            record_type = (release.get("record_type") or "").lower()
            tracks_n = release.get("nb_tracks") or 0
            genre_id = release.get("genre_id")
            release_artist = ((release.get("artist") or {}).get("name") or "")
            if record_type not in {"album", "mixtape", "ep", ""}:
                continue
            if tracks_n and (tracks_n < 5 or tracks_n > 36):
                continue
            if genre_id in NON_GENRES:
                continue
            rel_norm = normalize(release_artist)
            name_norm = normalize(display)
            if rel_norm and name_norm not in rel_norm and rel_norm not in name_norm:
                continue
            if should_skip_title(title):
                continue
            key = normalize(title)
            core = core_title(title)
            if key in existing_titles or core in existing_cores:
                continue
            date = release.get("release_date") or ""
            year = int(date[:4]) if date[:4].isdigit() else 0
            if year and year < 1988:
                continue
            picked.append(release)

        unique = []
        used = set()
        for release in picked:
            key = normalize(release.get("title") or "")
            if key in used:
                continue
            used.add(key)
            unique.append(release)
        unique.sort(key=lambda r: r.get("release_date") or "", reverse=True)
        unique = unique[:MAX_ALBUMS_PER_ARTIST]

        n = 0
        for release in unique:
            title = (release.get("title") or "").strip()
            try:
                songs = album_tracks(release.get("id"))
            except Exception as error:
                print("  tracks failed", title, error, flush=True)
                continue
            if len(songs) < 5 or len(songs) > 36:
                continue
            date = release.get("release_date") or ""
            year = int(date[:4]) if date[:4].isdigit() else 0
            cover = (
                release.get("cover_xl")
                or release.get("cover_big")
                or release.get("cover")
                or ""
            )
            max_id += 1
            albums.append(
                {
                    "id": max_id,
                    "title": title,
                    "artist": display,
                    "year": year or 0,
                    "genre": "Hip-Hop",
                    "cover": cover,
                    "songs": songs,
                }
            )
            added.append(f"{display} — {title} ({year})")
            existing_titles.add(normalize(title))
            existing_cores.add(core_title(title))
            existing_pairs.add((normalize(title), normalize(display)))
            n += 1
            print(f"  + {title} ({year}, {len(songs)} tracks)", flush=True)
            time.sleep(0.1)
        if n == 0:
            print("  still no albums", flush=True)
        time.sleep(0.15)

    (BASE / "js" / "albums.js").write_text(
        "const albums = " + json.dumps(albums, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(f"Retry added {len(added)}. Total {len(albums)}", flush=True)

    photos_path = BASE / "js" / "artistPhotos.js"
    raw_photos = photos_path.read_text(encoding="utf-8")
    raw_photos = raw_photos.replace("const artistPhotos =", "", 1).strip().rstrip(";")
    photos = json.loads(raw_photos)
    for name in found_artists:
        if name in photos:
            continue
        try:
            pic = search_photo(name)
        except Exception:
            pic = ""
        if pic:
            photos[name] = pic
            print("  photo", name, flush=True)
        time.sleep(0.1)
    photos_path.write_text(
        "const artistPhotos = "
        + json.dumps(photos, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
