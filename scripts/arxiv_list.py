"""List every arXiv paper announced in the past week for the given categories (all pages) and flag topic candidates.
usage: python3 -I arxiv_list.py <out.json> [category ...] [--config topic.json]
Categories default to sources.arxiv.categories; titles are matched against sources.arxiv.title_regex (topic_match).
Titles only (open each candidate's abs page for the abstract). Exit code 0 = every category fully listed, 2 = incomplete."""
import os, sys, re, time, json, html, urllib.request

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


cfg = topic_config()["sources"]["arxiv"]
out, cats = sys.argv[1], sys.argv[2:] or cfg["categories"]
TOPIC = re.compile(cfg["title_regex"], re.I)
items, status = {}, {}

def fetch(url):
    for a in range(5):
        try:
            return urllib.request.urlopen(url, timeout=90).read().decode("utf8")
        except Exception as e:
            print("retry", a + 1, e, file=sys.stderr); time.sleep(6 * (a + 1))
    return None

for c in cats:
    skip, total, got = 0, None, 0
    while total is None or skip < total:
        page = fetch(f"https://arxiv.org/list/{c}/pastweek?skip={skip}&show=2000")
        if page is None:
            break
        m = re.search(r"Total of ([\d,]+) entries", page)
        total = int(m.group(1).replace(",", "")) if m else 0
        pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", page, re.S)
        for dt, dd in pairs:
            i = re.search(r"/abs/(\d{4}\.\d{4,5})", dt)
            t = re.search(r"<div class='list-title mathjax'><span class='descriptor'>Title:</span>(.*?)</div>", dd, re.S)
            if i and t:
                title = " ".join(html.unescape(re.sub("<.*?>", "", t.group(1))).split())
                items.setdefault(i.group(1), {"id": i.group(1), "title": title, "cats": [], "topic_match": bool(TOPIC.search(title))})["cats"].append(c)
        got += len(pairs); skip += 2000
        if not pairs:
            break
        time.sleep(3)
    status[c] = {"total": total, "listed": got, "complete": total is not None and got >= total}
    print(c, status[c], file=sys.stderr)
json.dump(list(items.values()), open(out, "w"), ensure_ascii=False)
summary = {"source": "arXiv", "categories": status, "unique": len(items), "topic_match": sum(r["topic_match"] for r in items.values()),
           "complete": all(s["complete"] for s in status.values())}
print(json.dumps(summary, ensure_ascii=False))
sys.exit(0 if summary["complete"] else 2)
