"""Fetch every medRxiv (or bioRxiv) record posted in a date range (all pages) and flag topic / method candidates.
usage: python3 -I medrxiv_fetch.py <start YYYY-MM-DD> <end YYYY-MM-DD> <out.json> [--config topic.json]
sources.medrxiv: server ("medrxiv" or "biorxiv"), topic_regex (topic_match), method_regex (method_match); priority = both.
The details API returns 30 records per page; the cursor must advance by the number
of records returned (not by 100). Exit code 0 = all pages fetched, 2 = incomplete (see summary)."""
import os, sys, json, re, time, urllib.request

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


cfg = topic_config()["sources"]["medrxiv"]
SERVER = cfg.get("server", "medrxiv")
start, end, out = sys.argv[1:4]
TOPIC = re.compile(cfg["topic_regex"], re.I)
METHOD = re.compile(cfg["method_regex"], re.I)

def get(url, tries=6):
    for a in range(tries):
        try:
            return json.loads(urllib.request.urlopen(url, timeout=90).read().decode("utf8"))
        except Exception as e:
            print(f"retry {a + 1}: {e}", file=sys.stderr); time.sleep(min(60, 5 * 2 ** a))
    return None

items, cursor, total, failed = {}, 0, None, []
while total is None or cursor < total:
    d = get(f"https://api.biorxiv.org/details/{SERVER}/{start}/{end}/{cursor}/json")
    if d is None:
        failed.append(cursor); cursor += 30; continue  # skip this page, keep going, report it
    m = d["messages"][0]
    total = int(m.get("total", 0)); n = int(m.get("count", 0))
    for r in d.get("collection", []):
        key = (r["doi"], r["version"])
        t = r.get("title", "") + " " + r.get("abstract", "")
        items[key] = {"doi": r["doi"], "version": r["version"], "date": r["date"], "category": r.get("category"),
                      "title": " ".join(r.get("title", "").split()), "authors": r.get("authors"), "type": r.get("type"),
                      "license": r.get("license"), "abstract": r.get("abstract", ""),
                      "topic_match": bool(TOPIC.search(t)), "method_match": bool(METHOD.search(t))}
    if n == 0:
        break
    cursor += n; time.sleep(1)

rows = list(items.values())
for r in rows:
    r["priority"] = r["topic_match"] and r["method_match"]
json.dump(rows, open(out, "w"), ensure_ascii=False)
summary = {"source": SERVER, "interval": f"{start}:{end}", "total_reported": total, "fetched": len(rows),
           "failed_cursors": failed, "topic_match": sum(r["topic_match"] for r in rows), "priority": sum(r["priority"] for r in rows),
           "complete": not failed and total is not None and len(rows) >= total}
print(json.dumps(summary, ensure_ascii=False))
sys.exit(0 if summary["complete"] else 2)
