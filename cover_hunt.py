import json
import time
import urllib.parse
import urllib.request

UA = "RateYourHipHop/1.0"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

wiki_titles = [
    "Pilot_Talk",
    "Piñata_(album)",
    "Pinata_(Freddie_Gibbs_and_Madlib_album)",
    "C.A.S.H._(album)",
]
print("WIKI")
for t in wiki_titles:
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&prop=pageimages|pageterms"
        f"&titles={urllib.parse.quote(t)}&format=json&pithumbsize=1000"
    )
    data = get_json(url)
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        print(t, p.get("title"), p.get("thumbnail"))
    time.sleep(0.4)

print("\nDEEZER")
searches = [
    'artist:"Curren$y" album:"Pilot Talk"',
    "Currensy Pilot Talk 2010",
    'artist:"Blu" album:"C.A.S.H."',
    "Blu CASH 2011",
    "Domo Genesis Thirteen",
    "Domo Genesis Th1rt3en",
    'Freddie Gibbs Madlib "Piñata"',
    "Freddie Gibbs Piñata 2014",
]
for q in searches:
    url = "https://api.deezer.com/search/album?q=" + urllib.parse.quote(q) + "&limit=8"
    data = get_json(url)
    print("\nQ", q)
    for alb in data.get("data") or []:
        a = (alb.get("artist") or {}).get("name")
        print(" ", alb.get("id"), alb.get("nb_tracks"), a, "|", alb.get("title"))
    time.sleep(0.25)
