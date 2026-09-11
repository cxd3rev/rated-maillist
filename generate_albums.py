import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "RateYourHipHop/1.0"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tracks(album_id):
    songs = []
    url = f"https://api.deezer.com/album/{album_id}/tracks?limit=100"
    while url:
        data = get_json(url)
        for t in data.get("data") or []:
            if t.get("title"):
                songs.append(t["title"])
        url = data.get("next")
        time.sleep(0.08)
    return songs


def album_from_id(album_id):
    alb = get_json(f"https://api.deezer.com/album/{album_id}")
    songs = tracks(album_id)
    return {
        "cover": alb.get("cover_xl") or alb.get("cover_big") or "",
        "songs": songs,
        "deezerTitle": alb.get("title"),
        "deezerArtist": (alb.get("artist") or {}).get("name"),
    }


def norm(text):
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compatible_title(wanted, got):
    """Allow deluxe/edited editions; reject sequels, instrumentals, and unrelated titles."""
    w, g = norm(wanted), norm(got or "")
    if not w or not g:
        return False
    if w == g:
        return True
    if any(bad in g.split() for bad in ("instrumental", "instrumentals", "beats")) and "instrumental" not in w:
        return False
    version = {
        "deluxe", "expanded", "remaster", "remastered", "anniversary", "edition",
        "complete", "clean", "edited", "version", "intl", "international",
        "radio", "edit", "extended", "hot", "candles", "metime", "bonus", "track",
    }
    wt = [t for t in w.split() if t not in version]
    gt = [t for t in g.split() if t not in version]
    if "".join(wt) == "".join(gt):
        return True
    if wt == gt:
        return True
    if len(gt) >= len(wt) and gt[-len(wt):] == wt:
        extra = gt[: -len(wt)]
        if extra in ([], ["king", "push"]):
            return True
    if all(t in gt for t in wt):
        extra = [t for t in gt if t not in wt]
        if extra in ([], ["king", "push"], ["2025"]):
            return True
        if extra and extra[0] in ("2", "3", "4", "ii", "iii", "iv") and extra[0] not in wt:
            return False
        if "awesome" in extra or "god" in extra and "flygod" in w:
            return False
    return False


def clean_songs(songs):
    cleaned = [s for s in songs if "instrumental" not in s.lower()]
    return cleaned or songs


def js_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def render_album(album):
    song_lines = ",\n            ".join(f'"{js_escape(s)}"' for s in album["songs"])
    return f'''    {{
        id: {album["id"]},

        title: "{js_escape(album["title"])}",

        artist: "{js_escape(album["artist"])}",

        year: {album["year"]},

        genre: "Hip-Hop",

        cover:
            "{album["cover"]}",

        songs: [
            {song_lines}
        ]
    }}'''


CANONICAL_NEW = [
    ("good kid, m.A.A.d city", "Kendrick Lamar", 2012),
    ("R.A.P. Music", "Killer Mike", 2012),
    ("The Money Store", "Death Grips", 2012),
    ("Life Is Good", "Nas", 2012),
    ("Channel Orange", "Frank Ocean", 2012),
    ("Control System", "Ab-Soul", 2012),
    ("The Heist", "Macklemore & Ryan Lewis", 2012),
    ("God Forgives, I Don't", "Rick Ross", 2012),
    ("Cancer 4 Cure", "El-P", 2012),
    ("Reloaded", "Roc Marciano", 2012),
    ("Habits & Contradictions", "ScHoolboy Q", 2012),
    ("No Idols", "Domo Genesis & The Alchemist", 2012),
    ("Cruel Summer", "G.O.O.D. Music", 2012),
    ("1999", "Joey Bada$$", 2012),
    ("The Stoned Immaculate", "Curren$y", 2012),
    ("Yeezus", "Kanye West", 2013),
    ("Nothing Was the Same", "Drake", 2013),
    ("Run the Jewels", "Run the Jewels", 2013),
    ("Acid Rap", "Chance the Rapper", 2013),
    ("Because the Internet", "Childish Gambino", 2013),
    ("Long.Live.A$AP", "A$AP Rocky", 2013),
    ("My Name Is My Name", "Pusha T", 2013),
    ("Watching Movies with the Sound Off", "Mac Miller", 2013),
    ("Old", "Danny Brown", 2013),
    ("Wolf", "Tyler, The Creator", 2013),
    ("Doris", "Earl Sweatshirt", 2013),
    ("Born Sinner", "J. Cole", 2013),
    ("B.O.A.T.S. II: Me Time", "2 Chainz", 2013),
    ("BetterOffDEAD", "Flatbush Zombies", 2013),
    ("Indicud", "Kid Cudi", 2013),
    ("Piñata", "Freddie Gibbs & Madlib", 2014),
    ("2014 Forest Hills Drive", "J. Cole", 2014),
    ("Run the Jewels 2", "Run the Jewels", 2014),
    ("Oxymoron", "ScHoolboy Q", 2014),
    ("Cilvia Demo", "Isaiah Rashad", 2014),
    ("Faces", "Mac Miller", 2014),
    ("Dark Comedy", "Open Mike Eagle", 2014),
    ("Nobody's Smiling", "Common", 2014),
    ("Under Pressure", "Logic", 2014),
    ("PRhyme", "PRhyme", 2014),
    ("Honest", "Future", 2014),
    ("Days Before Rodeo", "Travis Scott", 2014),
    ("Cadillactica", "Big K.R.I.T.", 2014),
    ("The Pinkprint", "Nicki Minaj", 2014),
    ("Flygod", "Westside Gunn", 2014),
    ("Rodeo", "Travis Scott", 2015),
    ("Summertime '06", "Vince Staples", 2015),
    ("GO:OD AM", "Mac Miller", 2015),
    ("At.Long.Last.A$AP", "A$AP Rocky", 2015),
    ("Compton", "Dr. Dre", 2015),
    ("Darkest Before Dawn: The Prelude", "Pusha T", 2015),
    ("Cherry Bomb", "Tyler, The Creator", 2015),
    ("Surf", "Donnie Trumpet & The Social Experiment", 2015),
    ("Barter 6", "Young Thug", 2015),
    ("The Documentary 2", "The Game", 2015),
    ("Tetsuo & Youth", "Lupe Fiasco", 2015),
    ("Fetty Wap", "Fetty Wap", 2015),
    ("The Ecology", "Fashawn", 2015),
    ("We Got It from Here... Thank You 4 Your Service", "A Tribe Called Quest", 2016),
    ("Atrocity Exhibition", "Danny Brown", 2016),
    ("Malibu", "Anderson .Paak", 2016),
    ("Telefone", "Noname", 2016),
    ("The Sun's Tirade", "Isaiah Rashad", 2016),
    ("Blonde", "Frank Ocean", 2016),
    ("Jeffery", "Young Thug", 2016),
    ("untitled unmastered.", "Kendrick Lamar", 2016),
    ("Blank Face LP", "ScHoolboy Q", 2016),
    ("Coloring Book", "Chance the Rapper", 2016),
    ("Honor Killed the Samurai", "Ka", 2016),
    ("Imperial", "Denzel Curry", 2016),
    ("Still Brazy", "YG", 2016),
    ("Everybody Looking", "Gucci Mane", 2016),
    ("Lil Boat", "Lil Yachty", 2016),
    ("DAMN.", "Kendrick Lamar", 2017),
    ("4:44", "JAY-Z", 2017),
    ("Flower Boy", "Tyler, The Creator", 2017),
    ("Big Fish Theory", "Vince Staples", 2017),
    ("At What Cost", "GoldLink", 2017),
    ("Laila's Wisdom", "Rapsody", 2017),
    ("Saturation III", "BROCKHAMPTON", 2017),
    ("The Never Story", "JID", 2017),
    ("Without Warning", "21 Savage, Offset & Metro Boomin", 2017),
    ("Culture", "Migos", 2017),
    ("Playboi Carti", "Playboi Carti", 2017),
    ("Brick Body Kids Still Daydream", "Open Mike Eagle", 2017),
    ("Rather You Than Me", "Rick Ross", 2017),
    ("Droptopwop", "Gucci Mane & Metro Boomin", 2017),
    ("DAYTONA", "Pusha T", 2018),
    ("Some Rap Songs", "Earl Sweatshirt", 2018),
    ("ASTROWORLD", "Travis Scott", 2018),
    ("KIDS SEE GHOSTS", "KIDS SEE GHOSTS", 2018),
    ("CARE FOR ME", "Saba", 2018),
    ("Die Lit", "Playboi Carti", 2018),
    ("Veteran", "JPEGMAFIA", 2018),
    ("TA13OO", "Denzel Curry", 2018),
    ("KOD", "J. Cole", 2018),
    ("Swimming", "Mac Miller", 2018),
    ("TESTING", "A$AP Rocky", 2018),
    ("Tana Talk 3", "Benny the Butcher", 2018),
    ("Paraffin", "Armand Hammer", 2018),
    ("Book of Ryan", "Royce da 5'9\"", 2018),
    ("FM!", "Vince Staples", 2018),
    ("IGOR", "Tyler, The Creator", 2019),
    ("Bandana", "Freddie Gibbs & Madlib", 2019),
    ("GREY Area", "Little Simz", 2019),
    ("All My Heroes Are Cornballs", "JPEGMAFIA", 2019),
    ("Eve", "Rapsody", 2019),
    ("Let the Sun Talk", "MAVI", 2019),
    ("LAMB OVER RICE", "Action Bronson & The Alchemist", 2019),
    ("Ventura", "Anderson .Paak", 2019),
    ("ZUU", "Denzel Curry", 2019),
    ("The Lost Boy", "Cordae", 2019),
    ("Sli'merre", "Lil Nudy & Pi'erre Bourne", 2019),
    ("So Much Fun", "Young Thug", 2019),
    ("Psychodrama", "Dave", 2019),
    ("Hiding Places", "billy woods & Kenny Segal", 2019),
    ("Feet of Clay", "Earl Sweatshirt", 2019),
    ("RTJ4", "Run the Jewels", 2020),
    ("Circles", "Mac Miller", 2020),
    ("Pray for Paris", "Westside Gunn", 2020),
    ("A Written Testimony", "Jay Electronica", 2020),
    ("The Price of Tea in China", "Boldy James & The Alchemist", 2020),
    ("From King to a GOD", "Conway the Machine", 2020),
    ("Savage Mode II", "21 Savage & Metro Boomin", 2020),
    ("King's Disease", "Nas", 2020),
    ("Visions of Bodies Being Burned", "clipping.", 2020),
    ("Miles", "Blu & Exile", 2020),
    ("Descendants of Cain", "Ka", 2020),
    ("The Plugs I Met 2", "Benny the Butcher", 2020),
    ("Limbo", "Aminé", 2020),
    ("Shoot for the Stars Aim for the Moon", "Pop Smoke", 2020),
    ("CALL ME IF YOU GET LOST", "Tyler, The Creator", 2021),
    ("Haram", "Armand Hammer & The Alchemist", 2021),
    ("King's Disease II", "Nas", 2021),
    ("LP!", "JPEGMAFIA", 2021),
    ("The House Is Burning", "Isaiah Rashad", 2021),
    ("Bo Jackson", "Boldy James & The Alchemist", 2021),
    ("By the Time I Get to Phoenix", "Injury Reserve", 2021),
    ("The Off-Season", "J. Cole", 2021),
    ("Pray for Haiti", "Mach-Hommy", 2021),
    ("Smiling with No Teeth", "Genesis Owusu", 2021),
    ("Hitler Wears Hermes 8: Sincerely Adolf", "Westside Gunn", 2021),
    ("Balens Cho", "Mach-Hommy", 2021),
    ("Navy's Reprise", "Navy Blue", 2021),
    ("Super Tecmo Bo", "Boldy James", 2021),
    ("Mr. Morale & The Big Steppers", "Kendrick Lamar", 2022),
    ("Melt My Eyez See Your Future", "Denzel Curry", 2022),
    ("It's Almost Dry", "Pusha T", 2022),
    ("Aethiopes", "billy woods", 2022),
    ("King's Disease III", "Nas", 2022),
    ("NO THANK YOU", "Little Simz", 2022),
    ("God Don't Make Mistakes", "Conway the Machine", 2022),
    ("Few Good Things", "Saba", 2022),
    ("The Elephant Man's Bones", "Roc Marciano & The Alchemist", 2022),
    ("Learn 2 Swim", "redveil", 2022),
    ("Drill Music in Zion", "Lupe Fiasco", 2022),
    ("Louie", "Kenny Beats", 2022),
    ("Ramona Park Broke My Heart", "Vince Staples", 2022),
    ("SCARING THE HOES", "JPEGMAFIA & Danny Brown", 2023),
    ("We Buy Diabetic Test Strips", "Armand Hammer", 2023),
    ("Maps", "billy woods & Kenny Segal", 2023),
    ("UTOPIA", "Travis Scott", 2023),
    ("MICHAEL", "Killer Mike", 2023),
    ("Burning Desire", "MIKE", 2023),
    ("Quaranta", "Danny Brown", 2023),
    ("Beloved! Paradise! Jazz!?", "McKinley Dixon", 2023),
    ("Lahai", "Sampha", 2023),
    ("The Patience", "Mick Jenkins", 2023),
    ("VOIR DIRE", "Earl Sweatshirt & The Alchemist", 2023),
    ("Faith Is a Rock", "MIKE, Wiki & The Alchemist", 2023),
    ("And Then You Pray for Me", "Westside Gunn", 2023),
    ("Glorious Game", "El Michels Affair & Black Thought", 2023),
    ("Herbert", "Ab-Soul", 2023),
    ("GNX", "Kendrick Lamar", 2024),
    ("BLUE LIPS", "ScHoolboy Q", 2024),
    ("CHROMAKOPIA", "Tyler, The Creator", 2024),
    ("Dark Times", "Vince Staples", 2024),
    ("Samurai", "Lupe Fiasco", 2024),
    ("I LAY DOWN MY LIFE FOR YOU", "JPEGMAFIA", 2024),
    ("Alligator Bites Never Heal", "Doechii", 2024),
    ("The Auditorium Vol. 1", "Common & Pete Rock", 2024),
    ("Might Delete Later", "J. Cole", 2024),
    ("WE STILL DON'T TRUST YOU", "Future & Metro Boomin", 2024),
    ("Pinball", "MIKE & Tony Seltzer", 2024),
    ("Across the Tracks", "Boldy James & Nicholas Craven", 2024),
    ("The Thief Next to Jesus", "Ka", 2024),
    ("Cold Visions", "Bladee", 2024),
    ("King of the Mischievous South Vol. 2", "Denzel Curry", 2024),
    ("GOLLIWOG", "billy woods", 2025),
    ("God Does Like Ugly", "JID", 2025),
    ("Lotus", "Little Simz", 2025),
    ("Let God Sort Em Out", "Clipse", 2025),
    ("MAGIC, ALIVE!", "McKinley Dixon", 2025),
    ("From the Private Collection of Saba and No I.D.", "Saba & No I.D.", 2025),
    ("Live Laugh Love", "Earl Sweatshirt", 2025),
    ("Like a Ribbon", "John Glacier", 2025),
    ("Don't Look Down", "Kojey Radical", 2025),
    ("black british music (2025)", "Jim Legxacy", 2025),
    ("HOME?", "Wretch 32", 2025),
    ("The Boy Who Played the Harp", "Dave", 2025),
]


def main():
    source = Path("script.js").read_text(encoding="utf-8")
    pattern = re.compile(
        r"id:\s*(\d+),\s*title:\s*\"([^\"]+)\",\s*artist:\s*\"([^\"]+)\",\s*year:\s*(\d+),\s*genre:\s*\"([^\"]+)\",\s*cover:\s*\"([^\"]+)\",\s*songs:\s*\[(.*?)\]",
        re.S,
    )
    existing = []
    for m in pattern.finditer(source.split("const albums = [")[1].split("];")[0]):
        songs = re.findall(r"\"([^\"]+)\"", m.group(7))
        existing.append(
            {
                "id": int(m.group(1)),
                "title": m.group(2),
                "artist": m.group(3),
                "year": int(m.group(4)),
                "genre": m.group(5),
                "cover": m.group(6),
                "songs": songs,
            }
        )

    deezer = json.loads(Path("deezer_albums.json").read_text(encoding="utf-8"))
    by_norm = {}
    for item in deezer["found"]:
        if len(item.get("songs") or []) < 5:
            continue
        if not compatible_title(item["title"], item.get("deezerTitle") or ""):
            print("reject", item["title"], "->", item.get("deezerTitle"))
            continue
        by_norm[norm(item["title"])] = item

    ids = json.loads(Path("deezer_ids.json").read_text(encoding="utf-8"))
    extras = {
        "King of the Mischievous South Vol. 2": 614353722,
        "Pinball": 545854602,
        "Faith Is a Rock": 484876145,
        "Cheat Codes": 1052448642,
        "Take Care": 1622724,
        "Cruel Summer": 5943677,
        "PRhyme": 8865939,
        "Fetty Wap": 54266702,
        "Eve": 107878202,
        "Glorious Game": 385949677,
        "Run the Jewels": 882538842,
        "Under Pressure": 8844411,
        "Honest": 7707620,
        "Psychodrama": 820326491,
        "Miles": 146853022,
        "Drill Music in Zion": 329619147,
        "SCARING THE HOES": 415190837,
        "Samurai": 575083101,
        "HOME?": 725011061,
        "Piñata": 7498503,
        "Wolf": 6443023,
        "Doris": 6866562,
        "R.A.P. Music": 6230390,
        "B.O.A.T.S. II: Me Time": 6891211,
        "Run the Jewels 2": 880889112,
        "Flygod": 94183992,
        "Darkest Before Dawn: The Prelude": 11990992,
        "Culture": 304785627,
        "Ventura": 93038342,
        "The Plugs I Met 2": 205050702,
        "Hitler Wears Hermes 8: Sincerely Adolf": 254062152,
        "Balens Cho": 734170191,
        "From the Private Collection of Saba and No I.D.": 704134161,
        "black british music (2025)": 778617401,
        "The Forever Story": 371606587,
        "Thank Me Later": 576747,
        "Cypress Hill IV": 78554,
        "Sir Lucious Left Foot: The Son of Chico Dusty": 321204167,
        "Live.Love.A$AP": 267525872,
        "Book of Ryan": 59875222,
    }

    cover_overrides = {
        "Pilot Talk": "https://upload.wikimedia.org/wikipedia/en/4/4f/Pilottalk.jpg",
    }

    print("Fetching extra IDs if needed...")
    extra_data = {}
    force_fetch = {
        "Piñata",
        "Wolf",
        "Doris",
        "R.A.P. Music",
        "B.O.A.T.S. II: Me Time",
        "Run the Jewels 2",
        "Flygod",
        "Darkest Before Dawn: The Prelude",
        "Culture",
        "Ventura",
        "The Plugs I Met 2",
        "Hitler Wears Hermes 8: Sincerely Adolf",
        "Balens Cho",
        "From the Private Collection of Saba and No I.D.",
        "black british music (2025)",
        "The Forever Story",
        "Thank Me Later",
        "Cypress Hill IV",
        "Sir Lucious Left Foot: The Son of Chico Dusty",
        "Live.Love.A$AP",
        "Book of Ryan",
    }
    for title, aid in extras.items():
        cached = ids.get(title)
        if title not in force_fetch and cached and len(cached.get("songs") or []) >= 5:
            extra_data[norm(title)] = cached
        else:
            print(" ", title)
            extra_data[norm(title)] = album_from_id(aid)
            time.sleep(0.15)
        extra_data[norm(title)]["songs"] = clean_songs(extra_data[norm(title)].get("songs") or [])

    extra_data[norm("Honor Killed the Samurai")] = {
        "cover": "https://upload.wikimedia.org/wikipedia/en/5/58/Honor_Killed_the_Samurai_Album_Cover.jpg",
        "songs": [
            "Conflicted",
            "Just",
            "That Cold and Lonely",
            "Mourn at Night",
            "$",
            "Destined",
            "Ours",
            "Illicit Fields",
            "Finer Things / Tamahagene",
            "I Wish (Death Poem)",
        ],
    }

    aliases = {
        norm("Cypress Hill IV"): [norm("IV"), norm("Cypress Hill IV")],
        norm("Live.Love.A$AP"): [norm("LIVELOVEA$AP"), norm("Live Love ASAP"), norm("Live.Love.ASAP")],
        norm("R.E.D. Album"): [norm("The R.E.D. Album"), norm("RED Album")],
        norm("Man on the Moon II: The Legend of Mr. Rager"): [
            norm("Man on the Moon II The Legend of Mr Rager"),
            norm("Man on the Moon II"),
        ],
    }

    def lookup(title):
        keys = [norm(title)] + aliases.get(norm(title), [])
        for key in keys:
            if key in extra_data and extra_data[key].get("cover"):
                return extra_data[key]
            if key in by_norm:
                return by_norm[key]
        return None

    for album in existing:
        if album["title"] in cover_overrides:
            album["cover"] = cover_overrides[album["title"]]
            print("cover override", album["title"])
            continue
        hit = lookup(album["title"])
        if hit and hit.get("cover"):
            album["cover"] = hit["cover"]
            print("cover", album["title"])
        else:
            print("NO COVER", album["title"])

    new_albums = []
    next_id = max(a["id"] for a in existing) + 1
    for title, artist, year in CANONICAL_NEW:
        hit = lookup(title)
        if not hit or not hit.get("cover") or len(hit.get("songs") or []) < 4:
            print("SKIP NEW", title)
            continue
        songs = clean_songs(hit.get("songs") or [])
        if "piñata" in norm(title) and len(songs) > 17:
            songs = songs[:17]
        new_albums.append(
            {
                "id": next_id,
                "title": title,
                "artist": artist,
                "year": year,
                "cover": hit["cover"],
                "songs": songs,
            }
        )
        next_id += 1
        print("add", title, "n=", len(hit["songs"]))

    all_albums = existing + new_albums
    body = ",\n\n".join(render_album(a) for a in all_albums)
    js = "const albums = [\n\n" + body + "\n\n];\n"
    Path("albums_generated.js").write_text(js, encoding="utf-8")
    source = Path("script.js").read_text(encoding="utf-8")
    head, rest = source.split("const albums = [", 1)
    _, tail = rest.split("];", 1)
    Path("script.js").write_text(head + js + tail, encoding="utf-8")
    print("wrote albums_generated.js and script.js", "existing", len(existing), "new", len(new_albums), "total", len(all_albums))


if __name__ == "__main__":
    main()
