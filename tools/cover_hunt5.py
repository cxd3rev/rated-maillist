import json
import re
import urllib.request

UA = "Mozilla/5.0 RateYourHipHop/1.0"

urls = [
    "https://www.last.fm/music/Blu/C.A.S.H.",
    "https://www.last.fm/music/Blu/CASH",
    "https://www.last.fm/music/Domo+Genesis/Th1rt3en",
    "https://genius.com/albums/Blu/Cash",
    "https://genius.com/albums/Blu/C-a-s-h",
    "https://genius.com/albums/Domo-genesis/Th1rt3en",
    "https://genius.com/albums/Domo-genesis/Thirteen",
]

for url in urls:
    print("\n====", url)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", "ignore")
            print("status ok", len(html))
            for pat in [
                r'property="og:image" content="([^"]+)"',
                r'content="([^"]+)" property="og:image"',
                r'src="(https://lastfm[^"]+)"',
                r'(https://images\.genius\.com/[^"]+)',
            ]:
                m = re.search(pat, html)
                if m:
                    print(" HIT", m.group(1)[:180])
                    break
    except Exception as e:
        print("ERR", e)
