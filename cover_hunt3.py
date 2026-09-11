import json
import time
import urllib.parse
import urllib.request

UA = "RateYourHipHop/1.0"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

files = ["Pilottalk.jpg", "Freddie Gibbs Piñata.jpg", "Freddie_Gibbs_Piñata.jpg"]
print("WIKI FILES")
for f in files:
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&titles="
        + urllib.parse.quote("File:" + f)
        + "&prop=imageinfo&iiprop=url&format=json"
    )
    data = get_json(url)
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        print(f, p.get("title"), info.get("url"))

print("\nDISCOGS better")
params = [
    "release_title=C.A.S.H.&artist=Blu&type=release",
    "q=CASH+New+World+Color+Blu&type=release",
    "q=Domo+Genesis+13&type=release",
    "q=Th1rt3en+Domo&type=release",
    "release_title=Pilot+Talk&artist=Curren$y&type=release",
]
for p in params:
    url = "https://api.discogs.com/database/search?" + p + "&per_page=8"
    try:
        data = get_json(url)
        print("\n", p)
        for r in data.get("results") or []:
            print(" ", r.get("id"), r.get("year"), r.get("title"))
            print("   ", r.get("cover_image"))
    except Exception as e:
        print(p, e)
    time.sleep(1.1)
