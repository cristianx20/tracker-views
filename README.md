# Tracker views — actualizare automată

GitHub trage view-urile de pe YouTube și TikTok o dată pe zi și le pune în `data.json`.
În tracker apeși "Importă" și ia cifrele de aici.

## Ce e în repo
- `channels.json` — lista ta de conturi (o editezi când adaugi/scoți conturi)
- `run.py` — scriptul care rulează pe GitHub
- `fetch_core.py` — motorul de tras view-uri
- `.github/workflows/update.yml` — programarea zilnică
- `data.json` — rezultatul (îl generează GitHub, nu-l atingi)

## Cum adaugi un cont
Editezi `channels.json` și adaugi o linie, apoi commit. Exemplu:

```json
"yt-nume-nou": { "platform": "YT", "url": "https://www.youtube.com/@numenou", "brand": "mm" }
```

- `platform`: "YT" sau "TT"
- `brand`: "mm" (Monster Mash), "cctv", "pd" (Packdraw) sau "tjr"
- id-ul din față (ex. "yt-nume-nou") trebuie să fie același cu cel din tracker

## Rulează manual
Actions → Update views → Run workflow.
