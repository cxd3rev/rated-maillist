import json
import time
import urllib.parse
import urllib.request

UA = "RateYourHipHop/1.0 (student project)"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

queries = [
    ("Pilot Talk", "Curren$y"),
    ("C.A.S.H.", "Blu"),
    ("Th1rt3en", "Domo Genesis"),
    ("Piñata", "Freddie Gibbs"),
    ("Pinata", "Freddie Gibbs"),
]

for title, artist in queries:
    q = urllib.parse.quote(f'release:"{title}" AND artist:"{artist}"')
    url = f"https://musicbrainz.org/ws/2/release/?query={q}&fmt=json&limit=5"
    print("\n===", title, artist)
    try:
        data = get_json(url)
    except Exception as e:
        print("ERR", e)
        time.sleep(1.2)
        continue
    for rel in data.get("releases") or []:
        mbid = rel.get("id")
        ntracks = None
        med = rel.get("media") or []
        if med:
            ntracks = med[0].get("track-count")
        print(rel.get("title"), rel.get("date"), ntracks, mbid, [a["name"] for a in rel.get("artist-credit") or []])
        art = f"https://coverartarchive.org/release/{mbid}/front-500"
        try:
            req = urllib.request.Request(art, method="HEAD", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                print("  ART", resp.geturl(), resp.status)
        except Exception as e:
            print("  no art", e)
    time.sleep(1.1)
