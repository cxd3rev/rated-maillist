import json
import urllib.parse
import urllib.request

req = urllib.request.Request(
    "https://api.deezer.com/search/album?q=" + urllib.parse.quote("Migos Culture") + "&limit=12",
    headers={"User-Agent": "RateYourHipHop/1.0"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())
for alb in data.get("data") or []:
    a = (alb.get("artist") or {}).get("name")
    print(alb.get("id"), alb.get("nb_tracks"), a, alb.get("title"))
