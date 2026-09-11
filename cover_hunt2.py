import json
import time
import urllib.parse
import urllib.request

UA = "RateYourHipHop/1.0 (https://github.com/example)"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

print("WIKI images")
for t in ["Pilot_Talk", "Piñata_(Freddie_Gibbs_and_Madlib_album)"]:
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&prop=images|pageimages"
        f"&titles={urllib.parse.quote(t)}&format=json&pithumbsize=800&origin=*"
    )
    data = get_json(url)
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        print(t, "thumb", p.get("thumbnail"), "orig", p.get("original"))
        for im in (p.get("images") or [])[:12]:
            print("  img", im.get("title"))

print("\nDEEZER pinata", get_json("https://api.deezer.com/album/7498503").get("cover_xl"))

print("\nDISCOGS")
for q in ["Curren$y Pilot Talk", "Blu C.A.S.H.", "Domo Genesis Th1rt3en", "Domo Genesis Thirteen"]:
    url = "https://api.discogs.com/database/search?q=" + urllib.parse.quote(q) + "&type=release&per_page=5"
    try:
        data = get_json(url)
        print("\n", q)
        for r in data.get("results") or []:
            print(" ", r.get("id"), r.get("title"), r.get("year"), r.get("cover_image") or r.get("thumb"))
    except Exception as e:
        print(q, e)
    time.sleep(1.0)
