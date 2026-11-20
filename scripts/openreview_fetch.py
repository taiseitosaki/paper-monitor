"""Search OpenReview (API v2 full-text search, all venues) for submissions created since a date, one search per term.
usage: python3 -I openreview_fetch.py <since YYYY-MM-DD> <out.json> [--config topic.json]
Terms come from sources.openreview.terms. notes/search ranks by relevance and has no date filter, so each term is searched
with a large limit and results are filtered by creation date (cdate). Exit code 0 = every term searched, 2 = some terms failed."""
import os, sys, json, time, datetime, urllib.request, urllib.parse

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


TERMS = topic_config()["sources"]["openreview"]["terms"]
since, out = sys.argv[1], sys.argv[2]
since_ms = int(datetime.datetime.fromisoformat(since).replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)

def get(url, tries=6):
    for a in range(tries):
        try:
            return json.loads(urllib.request.urlopen(url, timeout=90).read().decode("utf8"))
        except Exception as e:
            print(f"retry {a + 1}: {e}", file=sys.stderr); time.sleep(min(60, 5 * 2 ** a))
    return None

v = lambda c, k: (c.get(k) or {}).get("value") if isinstance(c.get(k), dict) else c.get(k)
items, failed = {}, []
for term in TERMS:
    d = get("https://api2.openreview.net/notes/search?" + urllib.parse.urlencode({"term": term, "source": "forum", "limit": 1000}))
    if d is None:
        failed.append(term); continue
    for n in d.get("notes", []):
        if (n.get("cdate") or 0) < since_ms or n["id"] in items:
            continue
        c = n.get("content", {})
        items[n["id"]] = {"id": n["id"], "url": "https://openreview.net/forum?id=" + n["id"], "domain": n.get("domain"),
                          "venue": v(c, "venue"), "title": " ".join((v(c, "title") or "").split()), "abstract": v(c, "abstract") or "",
                          "created": datetime.datetime.fromtimestamp(n["cdate"] / 1000, datetime.timezone.utc).date().isoformat(),
                          "matched_term": term}
    time.sleep(1.5)
rows = sorted(items.values(), key=lambda r: r["created"], reverse=True)
json.dump(rows, open(out, "w"), ensure_ascii=False)
summary = {"source": "OpenReview", "since": since, "terms": len(TERMS), "failed_terms": failed, "found": len(rows), "complete": not failed}
print(json.dumps(summary, ensure_ascii=False))
sys.exit(0 if summary["complete"] else 2)
