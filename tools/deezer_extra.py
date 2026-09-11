import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RateYourHipHop/1.0"
queries = [
    "Denzel Curry King of the Mischievous South Vol. 2",
    "MIKE Tony Seltzer Pinball",
    "MIKE Wiki Alchemist Faith Is a Rock",
    "Navy Blue Ways of Knowing",
]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


for q in queries:
    data = get_json("https://api.deezer.com/search/album?q=" + urllib.parse.quote(q) + "&limit=5")
    print("\n", q)
    for alb in data.get("data") or []:
        a = (alb.get("artist") or {}).get("name")
        print(f"  {alb.get('id')} n={alb.get('nb_tracks')} {a} | {alb.get('title')}")
    time.sleep(0.2)
