import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "RateYourHipHop/1.0"

ALL = [
    ("existing", "My Beautiful Dark Twisted Fantasy", "Kanye West", 2010),
    ("existing", "To Pimp a Butterfly", "Kendrick Lamar", 2015),
    ("existing", "Alfredo", "Freddie Gibbs", 2020),
    ("existing", "The Forever Story", "JID", 2022),
    ("existing", "Sometimes I Might Be Introvert", "Little Simz", 2021),
    ("existing", "Cheat Codes", "Black Thought", 2022),
    ("existing", "Man on the Moon II: The Legend of Mr. Rager", "Kid Cudi", 2010),
    ("existing", "Thank Me Later", "Drake", 2010),
    ("existing", "Recovery", "Eminem", 2010),
    ("existing", "How I Got Over", "The Roots", 2010),
    ("existing", "The ArchAndroid", "Janelle Monae", 2010),
    ("existing", "IV", "Cypress Hill", 1998),
    ("existing", "Kush & Orange Juice", "Wiz Khalifa", 2010),
    ("existing", "Sir Lucious Left Foot: The Son of Chico Dusty", "Big Boi", 2010),
    ("existing", "The Appeal: Georgia's Most Wanted", "Gucci Mane", 2010),
    ("existing", "Teflon Don", "Rick Ross", 2010),
    ("existing", "Pilot Talk", "Curren$y", 2010),
    ("existing", "Take Care", "Drake", 2011),
    ("existing", "Section.80", "Kendrick Lamar", 2011),
    ("existing", "Watch the Throne", "JAY-Z", 2011),
    ("existing", "Undun", "The Roots", 2011),
    ("existing", "XXX", "Danny Brown", 2011),
    ("existing", "The Dreamer/The Believer", "Common", 2011),
    ("existing", "LIVELOVEA$AP", "A$AP Rocky", 2011),
    ("existing", "Lasers", "Lupe Fiasco", 2011),
    ("existing", "Cole World: The Sideline Story", "J. Cole", 2011),
    ("existing", "Return of 4Eva", "Big K.R.I.T.", 2011),
    ("existing", "Elmatic", "Elzhi", 2011),
    ("existing", "C.A.S.H.", "Blu", 2011),
    ("existing", "The R.E.D. Album", "Game", 2011),
    ("existing", "Th1rt3en", "Domo Genesis", 2011),
    ("existing", "Goblin", "Tyler, The Creator", 2011),
    ("new", "good kid, m.A.A.d city", "Kendrick Lamar", 2012),
    ("new", "R.A.P. Music", "Killer Mike", 2012),
    ("new", "The Money Store", "Death Grips", 2012),
    ("new", "Life Is Good", "Nas", 2012),
    ("new", "Channel ORANGE", "Frank Ocean", 2012),
    ("new", "Control System", "Ab-Soul", 2012),
    ("new", "The Heist", "Macklemore & Ryan Lewis", 2012),
    ("new", "God Forgives, I Don't", "Rick Ross", 2012),
    ("new", "Cancer 4 Cure", "El-P", 2012),
    ("new", "Reloaded", "Roc Marciano", 2012),
    ("new", "Habits & Contradictions", "ScHoolboy Q", 2012),
    ("new", "No Idols", "Domo Genesis", 2012),
    ("new", "Cruel Summer", "Kanye West", 2012),
    ("new", "1999", "Joey Bada$$", 2012),
    ("new", "The Stoned Immaculate", "Curren$y", 2012),
    ("new", "Yeezus", "Kanye West", 2013),
    ("new", "Nothing Was the Same", "Drake", 2013),
    ("new", "Run the Jewels", "Run the Jewels", 2013),
    ("new", "Acid Rap", "Chance the Rapper", 2013),
    ("new", "Because the Internet", "Childish Gambino", 2013),
    ("new", "Long.Live.A$AP", "A$AP Rocky", 2013),
    ("new", "My Name Is My Name", "Pusha T", 2013),
    ("new", "Watching Movies with the Sound Off", "Mac Miller", 2013),
    ("new", "Old", "Danny Brown", 2013),
    ("new", "Wolf", "Tyler, The Creator", 2013),
    ("new", "Doris", "Earl Sweatshirt", 2013),
    ("new", "Born Sinner", "J. Cole", 2013),
    ("new", "B.O.A.T.S. II: Me Time", "2 Chainz", 2013),
    ("new", "BetterOffDEAD", "Flatbush Zombies", 2013),
    ("new", "Indicud", "Kid Cudi", 2013),
    ("new", "Piñata", "Freddie Gibbs", 2014),
    ("new", "2014 Forest Hills Drive", "J. Cole", 2014),
    ("new", "Run the Jewels 2", "Run the Jewels", 2014),
    ("new", "Oxymoron", "ScHoolboy Q", 2014),
    ("new", "Cilvia Demo", "Isaiah Rashad", 2014),
    ("new", "Faces", "Mac Miller", 2014),
    ("new", "Dark Comedy", "Open Mike Eagle", 2014),
    ("new", "Nobody's Smiling", "Common", 2014),
    ("new", "Under Pressure", "Logic", 2014),
    ("new", "PRhyme", "Royce da 5'9\"", 2014),
    ("new", "Honest", "Future", 2014),
    ("new", "Days Before Rodeo", "Travis Scott", 2014),
    ("new", "Cadillactica", "Big K.R.I.T.", 2014),
    ("new", "The Pinkprint", "Nicki Minaj", 2014),
    ("new", "Flygod", "Westside Gunn", 2014),
    ("new", "Rodeo", "Travis Scott", 2015),
    ("new", "Summertime '06", "Vince Staples", 2015),
    ("new", "GO:OD AM", "Mac Miller", 2015),
    ("new", "At.Long.Last.A$AP", "A$AP Rocky", 2015),
    ("new", "Compton", "Dr. Dre", 2015),
    ("new", "Darkest Before Dawn", "Pusha T", 2015),
    ("new", "Cherry Bomb", "Tyler, The Creator", 2015),
    ("new", "Surf", "Donnie Trumpet", 2015),
    ("new", "Barter 6", "Young Thug", 2015),
    ("new", "The Documentary 2", "The Game", 2015),
    ("new", "Tetsuo & Youth", "Lupe Fiasco", 2015),
    ("new", "Fetty Wap", "Fetty Wap", 2015),
    ("new", "The Ecology", "Fashawn", 2015),
    ("new", "We Got It from Here... Thank You 4 Your Service", "A Tribe Called Quest", 2016),
    ("new", "Atrocity Exhibition", "Danny Brown", 2016),
    ("new", "Malibu", "Anderson .Paak", 2016),
    ("new", "Telefone", "Noname", 2016),
    ("new", "The Sun's Tirade", "Isaiah Rashad", 2016),
    ("new", "Blonde", "Frank Ocean", 2016),
    ("new", "JEFFERY", "Young Thug", 2016),
    ("new", "untitled unmastered.", "Kendrick Lamar", 2016),
    ("new", "Blank Face LP", "ScHoolboy Q", 2016),
    ("new", "Coloring Book", "Chance the Rapper", 2016),
    ("new", "Honor Killed the Samurai", "Ka", 2016),
    ("new", "Imperial", "Denzel Curry", 2016),
    ("new", "Still Brazy", "YG", 2016),
    ("new", "Everybody Looking", "Gucci Mane", 2016),
    ("new", "Lil Boat", "Lil Yachty", 2016),
    ("new", "DAMN.", "Kendrick Lamar", 2017),
    ("new", "4:44", "JAY-Z", 2017),
    ("new", "Flower Boy", "Tyler, The Creator", 2017),
    ("new", "Big Fish Theory", "Vince Staples", 2017),
    ("new", "At What Cost", "GoldLink", 2017),
    ("new", "Laila's Wisdom", "Rapsody", 2017),
    ("new", "SATURATION III", "BROCKHAMPTON", 2017),
    ("new", "The Never Story", "JID", 2017),
    ("new", "Without Warning", "21 Savage", 2017),
    ("new", "Culture", "Migos", 2017),
    ("new", "Playboi Carti", "Playboi Carti", 2017),
    ("new", "Brick Body Kids Still Daydream", "Open Mike Eagle", 2017),
    ("new", "Rather You Than Me", "Rick Ross", 2017),
    ("new", "DropTopWop", "Gucci Mane", 2017),
    ("new", "DAYTONA", "Pusha T", 2018),
    ("new", "Some Rap Songs", "Earl Sweatshirt", 2018),
    ("new", "ASTROWORLD", "Travis Scott", 2018),
    ("new", "KIDS SEE GHOSTS", "KIDS SEE GHOSTS", 2018),
    ("new", "CARE FOR ME", "Saba", 2018),
    ("new", "Die Lit", "Playboi Carti", 2018),
    ("new", "Veteran", "JPEGMAFIA", 2018),
    ("new", "TA13OO", "Denzel Curry", 2018),
    ("new", "KOD", "J. Cole", 2018),
    ("new", "Swimming", "Mac Miller", 2018),
    ("new", "TESTING", "A$AP Rocky", 2018),
    ("new", "Tana Talk 3", "Benny the Butcher", 2018),
    ("new", "Paraffin", "Armand Hammer", 2018),
    ("new", "Book of Ryan", "Royce da 5'9\"", 2018),
    ("new", "FM!", "Vince Staples", 2018),
    ("new", "IGOR", "Tyler, The Creator", 2019),
    ("new", "Bandana", "Freddie Gibbs", 2019),
    ("new", "GREY Area", "Little Simz", 2019),
    ("new", "All My Heroes Are Cornballs", "JPEGMAFIA", 2019),
    ("new", "Eve", "Rapsody", 2019),
    ("new", "Let the Sun Talk", "MAVI", 2019),
    ("new", "Lamb Over Rice", "Action Bronson", 2019),
    ("new", "Ventura", "Anderson .Paak", 2019),
    ("new", "ZUU", "Denzel Curry", 2019),
    ("new", "The Lost Boy", "Cordae", 2019),
    ("new", "Sli'merre", "Lil Nudy", 2019),
    ("new", "So Much Fun", "Young Thug", 2019),
    ("new", "Psychodrama", "Dave", 2019),
    ("new", "Hiding Places", "billy woods", 2019),
    ("new", "Feet of Clay", "Earl Sweatshirt", 2019),
    ("new", "RTJ4", "Run the Jewels", 2020),
    ("new", "Circles", "Mac Miller", 2020),
    ("new", "Pray for Paris", "Westside Gunn", 2020),
    ("new", "A Written Testimony", "Jay Electronica", 2020),
    ("new", "The Price of Tea in China", "Boldy James", 2020),
    ("new", "From King To A GOD", "Conway the Machine", 2020),
    ("new", "SAVAGE MODE II", "21 Savage", 2020),
    ("new", "King's Disease", "Nas", 2020),
    ("new", "Visions of Bodies Being Burned", "clipping.", 2020),
    ("new", "Miles", "Blu & Exile", 2020),
    ("new", "Descendants of Cain", "Ka", 2020),
    ("new", "The Plugs I Met 2", "Benny the Butcher", 2020),
    ("new", "Limbo", "Aminé", 2020),
    ("new", "Shoot for the Stars Aim for the Moon", "Pop Smoke", 2020),
    ("new", "CALL ME IF YOU GET LOST", "Tyler, The Creator", 2021),
    ("new", "Haram", "Armand Hammer", 2021),
    ("new", "King's Disease II", "Nas", 2021),
    ("new", "LP!", "JPEGMAFIA", 2021),
    ("new", "The House Is Burning", "Isaiah Rashad", 2021),
    ("new", "Bo Jackson", "Boldy James", 2021),
    ("new", "By the Time I Get to Phoenix", "Injury Reserve", 2021),
    ("new", "The Off-Season", "J. Cole", 2021),
    ("new", "Pray For Haiti", "Mach-Hommy", 2021),
    ("new", "Smiling with No Teeth", "Genesis Owusu", 2021),
    ("new", "Hitler Wears Hermes 8", "Westside Gunn", 2021),
    ("new", "Balens Cho", "Mach-Hommy", 2021),
    ("new", "Navy's Reprise", "Navy Blue", 2021),
    ("new", "Super Tecmo Bo", "Boldy James", 2021),
    ("new", "Mr. Morale & The Big Steppers", "Kendrick Lamar", 2022),
    ("new", "Melt My Eyez See Your Future", "Denzel Curry", 2022),
    ("new", "It's Almost Dry", "Pusha T", 2022),
    ("new", "Aethiopes", "billy woods", 2022),
    ("new", "King's Disease III", "Nas", 2022),
    ("new", "NO THANK YOU", "Little Simz", 2022),
    ("new", "God Don't Make Mistakes", "Conway the Machine", 2022),
    ("new", "Few Good Things", "Saba", 2022),
    ("new", "The Elephant Man's Bones", "Roc Marciano", 2022),
    ("new", "Learn 2 Swim", "redveil", 2022),
    ("new", "Drill Music in Zion", "Lupe Fiasco", 2022),
    ("new", "Louie", "Kenny Beats", 2022),
    ("new", "Ramona Park Broke My Heart", "Vince Staples", 2022),
    ("new", "SCARING THE HOES", "JPEGMAFIA", 2023),
    ("new", "We Buy Diabetic Test Strips", "Armand Hammer", 2023),
    ("new", "Maps", "billy woods", 2023),
    ("new", "UTOPIA", "Travis Scott", 2023),
    ("new", "MICHAEL", "Killer Mike", 2023),
    ("new", "Burning Desire", "MIKE", 2023),
    ("new", "Quaranta", "Danny Brown", 2023),
    ("new", "Beloved! Paradise! Jazz!?", "McKinley Dixon", 2023),
    ("new", "Lahai", "Sampha", 2023),
    ("new", "The Patience", "Mick Jenkins", 2023),
    ("new", "VOIR DIRE", "Earl Sweatshirt", 2023),
    ("new", "Faith is a Rock", "Navy Blue", 2023),
    ("new", "And Then You Pray For Me", "Westside Gunn", 2023),
    ("new", "Glorious Game", "Black Thought", 2023),
    ("new", "Herbert", "Ab-Soul", 2023),
    ("new", "GNX", "Kendrick Lamar", 2024),
    ("new", "BLUE LIPS", "ScHoolboy Q", 2024),
    ("new", "CHROMAKOPIA", "Tyler, The Creator", 2024),
    ("new", "Dark Times", "Vince Staples", 2024),
    ("new", "Samurai", "Lupe Fiasco", 2024),
    ("new", "I LAY DOWN MY LIFE FOR YOU", "JPEGMAFIA", 2024),
    ("new", "Alligator Bites Never Heal", "Doechii", 2024),
    ("new", "The Auditorium Vol. 1", "Common", 2024),
    ("new", "Might Delete Later", "J. Cole", 2024),
    ("new", "WE STILL DON'T TRUST YOU", "Future", 2024),
    ("new", "Pinball", "Open Mike Eagle", 2024),
    ("new", "Across the Tracks", "Boldy James", 2024),
    ("new", "The Thief Next to Jesus", "Ka", 2024),
    ("new", "Cold Visions", "Bladee", 2024),
    ("new", "King of the Mischievous South Vol. 2", "Big K.R.I.T.", 2024),
    ("new", "GOLLIWOG", "billy woods", 2025),
    ("new", "God Does Like Ugly", "JID", 2025),
    ("new", "Lotus", "Little Simz", 2025),
    ("new", "Let God Sort Em Out", "Clipse", 2025),
    ("new", "MAGIC, ALIVE!", "McKinley Dixon", 2025),
    ("new", "From the Private Collection of Saba and No ID", "Saba", 2025),
    ("new", "LIVE LAUGH LOVE", "Earl Sweatshirt", 2025),
    ("new", "Like a Ribbon", "John Glacier", 2025),
    ("new", "Don't Look Down", "Kojey Radical", 2025),
    ("new", "black british music", "Jim Legxacy", 2025),
    ("new", "HOME?", "Wretch 32", 2025),
    ("new", "The Boy Who Played the Harp", "Dave", 2025),
]


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tokens(text: str):
    text = text.lower().replace("&", "and")
    text = re.sub(r"[^a-z0-9$]+", " ", text)
    return set(text.split()) - {"the", "a", "an", "and", "of", "to"}


def title_ok(wanted: str, got: str) -> bool:
    wt, gt = tokens(wanted), tokens(got)
    if not wt:
        return False
    overlap = len(wt & gt) / len(wt)
    if overlap >= 0.7:
        return True
    wn = re.sub(r"[^a-z0-9]+", "", wanted.lower())
    gn = re.sub(r"[^a-z0-9]+", "", got.lower())
    return wn in gn or gn in wn


def search_album(title: str, artist: str):
    q = urllib.parse.quote(f'album:"{title}" artist:"{artist}"')
    data = get_json(f"https://api.deezer.com/search/album?q={q}&limit=15")
    albums = data.get("data") or []
    if not albums:
        q = urllib.parse.quote(f"{artist} {title}")
        data = get_json(f"https://api.deezer.com/search/album?q={q}&limit=15")
        albums = data.get("data") or []
    for alb in albums:
        got_title = alb.get("title") or ""
        got_artist = (alb.get("artist") or {}).get("name") or ""
        if not title_ok(title, got_title):
            continue
        if tokens(artist) and len(tokens(artist) & tokens(got_artist)) == 0:
            if artist.lower() not in got_artist.lower() and got_artist.lower() not in artist.lower():
                continue
        return alb
    return None


def album_tracks(album_id: int):
    songs = []
    url = f"https://api.deezer.com/album/{album_id}/tracks?limit=100"
    while url:
        data = get_json(url)
        for t in data.get("data") or []:
            name = t.get("title")
            if name:
                songs.append(name)
        url = data.get("next")
        if url:
            time.sleep(0.15)
    return songs


def main():
    found = []
    missing = []
    for i, (kind, title, artist, year) in enumerate(ALL, 1):
        print(f"[{i}/{len(ALL)}] {artist} - {title}", flush=True)
        try:
            alb = search_album(title, artist)
            if not alb:
                missing.append({"kind": kind, "title": title, "artist": artist, "year": year, "why": "no album"})
                print("  miss")
                time.sleep(0.2)
                continue
            songs = album_tracks(alb["id"])
            cover = alb.get("cover_xl") or alb.get("cover_big") or alb.get("cover_medium") or ""
            rec = {
                "kind": kind,
                "title": title,
                "displayArtist": artist,
                "year": year,
                "deezerTitle": alb.get("title"),
                "deezerArtist": (alb.get("artist") or {}).get("name"),
                "cover": cover,
                "songs": songs,
            }
            found.append(rec)
            print(f"  ok {alb.get('title')} n={len(songs)}")
        except Exception as exc:
            missing.append({"kind": kind, "title": title, "artist": artist, "year": year, "why": str(exc)})
            print("  err", exc)
        time.sleep(0.2)

    (ROOT / "data" / "deezer_albums.json").write_text(
        json.dumps({"found": found, "missing": missing}, indent=2),
        encoding="utf-8",
    )
    print("found", len(found), "missing", len(missing))


if __name__ == "__main__":
    main()
