import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

EXISTING = [
    ("My Beautiful Dark Twisted Fantasy", "Kanye West", 2010),
    ("To Pimp a Butterfly", "Kendrick Lamar", 2015),
    ("Alfredo", "Freddie Gibbs & The Alchemist", 2020),
    ("The Forever Story", "JID", 2022),
    ("Sometimes I Might Be Introvert", "Little Simz", 2021),
    ("Cheat Codes", "Black Thought & Danger Mouse", 2022),
    ("Man on the Moon II: The Legend of Mr. Rager", "Kid Cudi", 2010),
    ("Thank Me Later", "Drake", 2010),
    ("Recovery", "Eminem", 2010),
    ("How I Got Over", "The Roots", 2010),
    ("The ArchAndroid", "Janelle Monáe", 2010),
    ("IV", "Cypress Hill", 1998),
    ("Kush & Orange Juice", "Wiz Khalifa", 2010),
    ("Sir Lucious Left Foot: The Son of Chico Dusty", "Big Boi", 2010),
    ("The Appeal: Georgia's Most Wanted", "Gucci Mane", 2010),
    ("Teflon Don", "Rick Ross", 2010),
    ("Pilot Talk", "Curren$y", 2010),
    ("Take Care", "Drake", 2011),
    ("Section.80", "Kendrick Lamar", 2011),
    ("Watch the Throne", "Jay-Z & Kanye West", 2011),
    ("Undun", "The Roots", 2011),
    ("XXX", "Danny Brown", 2011),
    ("The Dreamer/The Believer", "Common", 2011),
    ("Live.Love.A$AP", "A$AP Rocky", 2011),
    ("Lasers", "Lupe Fiasco", 2011),
    ("Cole World: The Sideline Story", "J. Cole", 2011),
    ("Return of 4Eva", "Big K.R.I.T.", 2011),
    ("Elmatic", "Elzhi", 2011),
    ("C.A.S.H.", "Blu", 2011),
    ("The R.E.D. Album", "The Game", 2011),
    ("Th1rt3en", "Domo Genesis", 2011),
    ("Goblin", "Tyler, The Creator", 2011),
]

NEW = [
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
    ("Cruel Summer", "Kanye West & G.O.O.D. Music", 2012),
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
    ("LAMB OVER RICE", "Action Bronson", 2019),
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
    ("Faith Is a Rock", "Navy Blue", 2023),
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
    ("Pinball", "Open Mike Eagle", 2024),
    ("Across the Tracks", "Boldy James & Nicholas Craven", 2024),
    ("The Thief Next to Jesus", "Ka", 2024),
    ("Cold Visions", "Bladee", 2024),
    ("King of the Mischievous South Vol. 2", "Big K.R.I.T.", 2024),
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


def get_json(url: str):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RateYourHipHop/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def upsample(url: str) -> str:
    if not url:
        return ""
    return re.sub(r"\d+x\d+bb", "600x600bb", url)


def normalize(text: str) -> str:
    text = text.lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_score(wanted: str, got: str) -> int:
    a, b = normalize(wanted), normalize(got)
    if a == b:
        return 100
    if a in b or b in a:
        return 80
    wa, wb = set(a.split()), set(b.split())
    if not wa:
        return 0
    return int(100 * len(wa & wb) / len(wa))


def search_album(title: str, artist: str, year: int):
    term = urllib.parse.quote(f"{artist} {title}")
    url = (
        "https://itunes.apple.com/search"
        f"?term={term}&entity=album&limit=10&country=US"
    )
    try:
        data = get_json(url)
    except Exception as exc:
        return {"error": str(exc)}

    best = None
    best_score = -1
    for item in data.get("results", []):
        if item.get("wrapperType") != "collection" and item.get("collectionType") not in (
            "Album",
            None,
        ):
            continue
        got_title = item.get("collectionName") or ""
        got_artist = item.get("artistName") or ""
        score = title_score(title, got_title) + title_score(artist, got_artist) * 0.6
        got_year = str(item.get("releaseDate", ""))[:4]
        if got_year == str(year):
            score += 15
        if score > best_score:
            best_score = score
            best = item

    if not best or best_score < 50:
        return {"error": "no match", "score": best_score}

    collection_id = best["collectionId"]
    lookup = get_json(
        f"https://itunes.apple.com/lookup?id={collection_id}&entity=song&limit=80"
    )
    songs = []
    for item in lookup.get("results", []):
        if item.get("wrapperType") == "track" and item.get("kind") == "song":
            name = item.get("trackName") or ""
            if name:
                songs.append(name)

    return {
        "title": title,
        "artist": artist,
        "year": year,
        "itunesTitle": best.get("collectionName"),
        "itunesArtist": best.get("artistName"),
        "cover": upsample(best.get("artworkUrl100", "")),
        "songs": songs,
        "score": best_score,
    }


def main():
    existing_results = []
    new_results = []
    missing = []

    print("Fetching existing covers...")
    for title, artist, year in EXISTING:
        print(f"  {artist} - {title}")
        result = search_album(title, artist, year)
        if result.get("cover"):
            existing_results.append(result)
        else:
            missing.append(("existing", title, artist, year, result))
        time.sleep(0.25)

    print("Fetching new albums...")
    for title, artist, year in NEW:
        print(f"  {artist} - {title}")
        result = search_album(title, artist, year)
        if result.get("cover") and result.get("songs"):
            new_results.append(result)
        else:
            missing.append(("new", title, artist, year, result))
        time.sleep(0.25)

    out = Path(__file__).with_name("album_fetch.json")
    out.write_text(
        json.dumps(
            {
                "existing": existing_results,
                "new": new_results,
                "missing": [
                    {
                        "kind": kind,
                        "title": title,
                        "artist": artist,
                        "year": year,
                        "result": result,
                    }
                    for kind, title, artist, year, result in missing
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out}")
    print(f"existing ok={len(existing_results)} new ok={len(new_results)} missing={len(missing)}")


if __name__ == "__main__":
    main()
