import json
import time
import urllib.parse
import urllib.request

UA = "RateYourHipHop/1.0"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

print("DEEZER wolf/doris")
for q in ['Tyler "Wolf"', "Wolf Tyler The Creator", "Doris Earl Sweatshirt"]:
    url = "https://api.deezer.com/search/album?q=" + urllib.parse.quote(q) + "&limit=10"
    data = get_json(url)
    print("\n", q)
    for alb in data.get("data") or []:
        a = (alb.get("artist") or {}).get("name")
        print(" ", alb.get("id"), alb.get("nb_tracks"), a, "|", alb.get("title"))
    time.sleep(0.2)

print("\nITUNES")
for term in ["Blu CASH rap", "Domo Genesis Th1rt3en", "Currensy Pilot Talk", "Cassidy C.A.S.H."]:
    url = "https://itunes.apple.com/search?term=" + urllib.parse.quote(term) + "&entity=album&limit=8"
    try:
        data = get_json(url)
        print("\n", term)
        for r in data.get("results") or []:
            print(" ", r.get("collectionId"), r.get("trackCount"), r.get("artistName"), "|", r.get("collectionName"))
            art = r.get("artworkUrl100", "").replace("100x100bb", "1000x1000bb")
            print("   ", art[:90])
    except Exception as e:
        print(term, e)
    time.sleep(1.5)
