import json
import urllib.parse
import urllib.request

queries = [
    "https://itunes.apple.com/search?term=Curren%24y+Pilot+Talk&entity=album&limit=15",
    "https://itunes.apple.com/search?term=Freddie+Gibbs+Madlib+Pinata&entity=album&limit=10",
    "https://itunes.apple.com/search?term=Tyler+the+Creator+Wolf&entity=album&limit=8",
    "https://itunes.apple.com/search?term=Earl+Sweatshirt+Doris&entity=album&limit=8",
]
for url in queries:
    print("\n===", url[:80])
    req = urllib.request.Request(url, headers={"User-Agent": "RateYourHipHop/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        for r in data.get("results") or []:
            print(r.get("collectionId"), r.get("trackCount"), r.get("artistName"), r.get("collectionName")[:60])
    except Exception as e:
        print(e)
    import time
    time.sleep(1.2)
