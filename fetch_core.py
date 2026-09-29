"""Monthly view tracker for Cristian's tracker artifact.
Input: channels.json = {id: {platform, url, videos?, channelId?, months?}}
Output: out.json with the same ids, updated: videos (id -> {v, d}), months (YYYY-MM -> {n, v}), recent (last 15 views), updated.
Only clips posted in a month count toward that month. Run: python3 updater.py channels.json out.json"""
import json, re, subprocess, sys, datetime, urllib.request, ssl

CTX = ssl._create_unverified_context()
def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"})
    return urllib.request.urlopen(req, context=CTX, timeout=40).read().decode("utf-8", "ignore")
def ytdlp(url, fmt, n=250):
    out = subprocess.run(["yt-dlp", "--no-check-certificates", "--flat-playlist", "--playlist-end", str(n), "--print", fmt, url],
                         capture_output=True, text=True, timeout=300).stdout
    return [l.split("|") for l in out.strip().splitlines() if "|" in l]

TZ = None
try:
    from zoneinfo import ZoneInfo; TZ = ZoneInfo("Europe/Bucharest")
except Exception: pass
def short_date(vid):
    """Publish date of one Short, from the date shown for that clip on its page.
    (The page also carries dates of other recommended Shorts, so only this field is trusted.)"""
    html = get("https://www.youtube.com/shorts/" + vid)
    m = re.search(r'"publishDate":\{"simpleText":"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})"\}', html)
    if m:
        mon = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(m.group(1)) + 1
        return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}"
    m = re.search(r'"microformat":\{"playerMicroformatRenderer".*?"publishDate":"(\d{4}-\d\d-\d\d)', html, re.S)
    if m: return m.group(1)
    raise RuntimeError("no date for " + vid)

def month_start(offset=0):
    t = datetime.date.today().replace(day=1)
    for _ in range(offset): t = (t - datetime.timedelta(days=1)).replace(day=1)
    return t.isoformat()

def yt(c):
    base = re.sub(r"/(shorts|videos|featured)/?$", "", c["url"].split("?")[0].rstrip("/"))
    rows = ytdlp(base + "/shorts", "%(id)s|%(view_count)s", 300)   # newest first, views only
    old = c.get("videos") or {}
    cache = {vid: o["d"] for vid, o in old.items() if o.get("d")}
    fetched = [0]
    def d_at(i):
        vid = rows[i][0]
        if vid not in cache:
            import time; time.sleep(0.8); fetched[0] += 1
            cache[vid] = short_date(vid)
        return cache[vid]
    def first_older(lo, since):
        """first index in [lo, len) whose date is before `since` (dates only go down along the list)"""
        hi = len(rows)
        while lo < hi:
            mid = (lo + hi) // 2
            if d_at(mid) < since: hi = mid
            else: lo = mid + 1
        return lo
    cur, prev = month_start(0), month_start(1)
    b1 = first_older(0, cur) if rows else 0
    b2 = first_older(b1, prev) if rows else 0
    out = []
    for i, (vid, v) in enumerate(rows[:b2]):
        mk = (cur if i < b1 else prev)[:7]
        out.append((vid, int(v) if v.isdigit() else 0, cache.get(vid) or (mk + "-01")))
    c["_fetched"] = fetched[0]
    c["_recent"] = [int(v) if v.isdigit() else 0 for _, v in rows[:15]]
    return out

def tt(c):
    rows = ytdlp(c["url"], "%(id)s|%(view_count)s|%(upload_date)s", 200)
    return [(vid, int(v) if v.isdigit() else 0, f"{d[:4]}-{d[4:6]}-{d[6:]}" if d.isdigit() else None) for vid, v, d in rows]

def ig(c):
    """Own Instagram professional account, via the official Instagram API (token stored on the channel)."""
    import json as _j, time
    tok = c.get("igToken")
    if not tok: raise RuntimeError("lipseste tokenul Instagram")
    # long-lived tokens last 60 days; refresh when older than 30
    at = c.get("igTokenAt")
    if not at or (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))).days >= 30:
        try:
            r = _j.loads(get("https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=" + tok))
            if r.get("access_token"):
                c["igToken"] = tok = r["access_token"]
                c["igTokenAt"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception: pass
    since = month_start(1)
    url = "https://graph.instagram.com/me/media?fields=id,timestamp,media_type,media_product_type&limit=100&access_token=" + tok
    items = []
    while url:
        page = _j.loads(get(url))
        stop = False
        for m in page.get("data", []):
            dt = datetime.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            d = (dt.astimezone(TZ) if TZ else dt).date().isoformat()
            if d < since: stop = True; break
            if m.get("media_type") != "VIDEO": continue
            items.append((m["id"], d))
        url = None if stop else (page.get("paging") or {}).get("next")
    rows = []
    for mid, d in items:
        v = 0
        try:
            r = _j.loads(get(f"https://graph.instagram.com/{mid}/insights?metric=views&access_token={tok}"))
            x = (r.get("data") or [{}])[0]
            v = (x.get("values") or [{}])[0].get("value") or (x.get("total_value") or {}).get("value") or 0
        except Exception: pass
        rows.append((mid, int(v), d)); time.sleep(0.2)
    return rows

def update(c):
    rows = yt(c) if c["platform"] == "YT" else (ig(c) if c["platform"] == "IG" else tt(c))   # newest first
    old = c.get("videos") or {}
    vids = []
    for vid, v, d in rows:
        d = d or (old.get(vid) or {}).get("d")
        vids.append([vid, v, d])
    # clips without a known date take the date of the next older dated clip (the list is newest first)
    nxt = None
    for r in reversed(vids):
        if r[2]: nxt = r[2]
        elif nxt: r[2] = nxt
    MIN = {"tjr": 1000}
    min_v = MIN.get(c.get("brand"), 0)
    months = dict(c.get("months") or {})
    cur = {}
    for vid, v, d in vids:
        if not d: continue
        mk = d[:7]; m = cur.setdefault(mk, {"n": 0, "v": 0, "pn": 0, "pv": 0})
        m["n"] += 1; m["v"] += v
        if v >= min_v:
            m["pn"] += 1; m["pv"] += v
    months.update(cur)   # months still visible on the channel are recounted, older ones stay as they were
    keep = (datetime.date.today().replace(day=1) - datetime.timedelta(days=62)).isoformat()
    c["videos"] = {vid: {"v": v, "d": d} for vid, v, d in vids if d and d >= keep}
    c["months"] = months
    c["recent"] = c.pop("_recent", None) or [v for _, v, _ in vids[:15]]
    c["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    c.pop("error", None)
    return c

if __name__ == "__main__":
    chans = json.load(open(sys.argv[1]))
    for cid, c in chans.items():
        if c.get("platform") not in ("YT", "TT", "IG"): continue
        if c.get("platform") == "IG" and not c.get("igToken"): continue
        try: update(c); print(cid, "ok", {k: v for k, v in c["months"].items() if k >= "2026-08"})
        except Exception as e: c["error"] = str(e)[:200]; print(cid, "error", e)
    json.dump(chans, open(sys.argv[2], "w"))
