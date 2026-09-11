import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RateYourHipHop/1.0"

QUERIES = [
    ("Cheat Codes", "Danger Mouse", 2022, "existing"),
    ("Th1rt3en", "Domo Genesis", 2011, "existing"),
    ("Take Care", "Drake", 2011, "existing"),
    ("C.A.S.H.", "Blu", 2011, "existing"),
    ("Cruel Summer", "GOOD Music", 2012, "new"),
    ("PRhyme", "PRhyme", 2014, "new"),
    ("Fetty Wap", "Fetty Wap", 2015, "new"),
    ("Honor Killed the Samurai", "Kaseem Ryan", 2016, "new"),
    ("Eve", "Rapsody", 2019, "new"),
    ("Faith of a Rock", "Navy Blue", 2023, "new"),
    ("Glorious Game", "El Michels Affair", 2023, "new"),
    ("Pinball", "Open Mike Eagle", 2024, "new"),
    ("King of the Mischievous South 2", "Big K.R.I.T.", 2024, "new"),
    ("Run the Jewels", "Run the Jewels", 2013, "new"),
    ("Under Pressure", "Logic", 2014, "new"),
    ("Honest", "Future", 2014, "new"),
    ("Psychodrama", "Dave", 2019, "new"),
    ("Miles", "Blu Exile", 2020, "new"),
    ("Drill Music in Zion", "Lupe Fiasco", 2022, "new"),
    ("SCARING THE HOES", "Danny Brown", 2023, "new"),
    ("Samurai", "Lupe Fiasco", 2024, "new"),
    ("HOME?", "Wretch 32", 2025, "new"),
]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def dump_search(title, artist):
    q = urllib.parse.quote(f"{artist} {title}")
    data = get_json(f"https://api.deezer.com/search/album?q={q}&limit=8")
    print(f"\n=== {artist} - {title} ===")
    for alb in data.get("data") or []:
        a = (alb.get("artist") or {}).get("name")
        print(f"  {alb.get('id')} | {alb.get('nb_tracks')} | {a} | {alb.get('title')}")


if __name__ == "__main__":
    for title, artist, year, kind in QUERIES:
        try:
            dump_search(title, artist)
        except Exception as e:
            print("err", title, e)
        time.sleep(0.25)
