"""
Rulează pe GitHub Actions o dată pe zi.
Citește channels.json (lista ta de conturi), trage view-urile de pe YouTube și TikTok,
și scrie data.json — fișierul pe care tracker-ul îl importă cu un singur buton.

Nu ai nevoie să-l rulezi manual. GitHub îl rulează singur.
"""
import json, datetime, os
import fetch_core as core

def main():
    chans = json.load(open("channels.json"))
    for cid, c in chans.items():
        plat = c.get("platform")
        if plat not in ("YT", "TT"):        # Instagram rămâne manual în tracker
            continue
        try:
            core.update(c)
            m = {k: v for k, v in c.get("months", {}).items() if k >= "2026-08"}
            print(cid, "ok", m)
        except Exception as e:
            c["error"] = str(e)[:200]
            print(cid, "EROARE", e)

    # data.json: doar ce are nevoie tracker-ul (compact, fără lista întreagă de videoclipuri)
    out = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "channels": {}}
    for cid, c in chans.items():
        if c.get("platform") not in ("YT", "TT"):
            continue
        out["channels"][cid] = {
            "brand": c.get("brand"),
            "platform": c.get("platform"),
            "url": c.get("url"),
            "label": c.get("label") or c.get("url", "").rstrip("/").split("@")[-1],
            "months": c.get("months", {}),
            "recent": c.get("recent", []),
            "updated": c.get("updated"),
            "error": c.get("error"),
        }
    json.dump(out, open("data.json", "w"), separators=(",", ":"))
    # channels.json păstrează videos/months, ca data viitoare să fie mai rapid
    json.dump(chans, open("channels.json", "w"), indent=2)
    print("Gata. Scris data.json cu", len(out["channels"]), "conturi.")

if __name__ == "__main__":
    main()
