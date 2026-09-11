import json
import time
import urllib.parse
import urllib.request

UA = "RateYourHipHop/1.0"

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

queries = [
    "Killer Mike RAP Music",
    "2 Chainz BOATS II Me Time",
    "Run the Jewels 2",
    "Westside Gunn Flygod",
    "Pusha T Darkest Before Dawn",
    "Migos Culture 2017",
    "Anderson Paak Ventura",
    "Benny the Butcher The Plugs I Met 2",
    "Westside Gunn Hitler Wears Hermes 8 Sincerely Adolf",
    "Mach-Hommy Balens Cho",
    "Saba No I.D. Private Collection",
    "Jim Legxacy black british music",
    "JID The Forever Story",
    "Drake Thank Me Later",
    "Cypress Hill IV",
    "Big Boi Sir Lucious Left Foot",
    "ASAP Rocky LIVELOVEASAP",
    "ASAP Rocky Live Love ASAP",
]
for q in queries:
    url = "https://api.deezer.com/search/album?q=" + urllib.parse.quote(q) + "&limit=6"
    data = get_json(url)
    print("\nQ", q)
    for alb in data.get("data") or []:
        a = (alb.get("artist") or {}).get("name")
        line = f"  {alb.get('id')} {alb.get('nb_tracks')} {a} | {alb.get('title')}"
        print(line.encode("ascii", "replace").decode("ascii"))
    time.sleep(0.2)
