"""Search PubMed (E-utilities, GET only) for recent papers matching sources.pubmed.term and fetch titles/abstracts.
usage: python3 -I pubmed_fetch.py <days back (entrez date)> <out.json> [--config topic.json]
Exit code 0 = search and all fetches succeeded, 2 = incomplete (see summary)."""
import os, sys, json, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


TERM = topic_config()["sources"]["pubmed"]["term"]
days, out = int(sys.argv[1]), sys.argv[2]
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def get(url, tries=6):
    for a in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "paper-monitor/1.0"}), timeout=90).read()
        except Exception as e:
            print(f"retry {a + 1}: {e}", file=sys.stderr); time.sleep(min(60, 4 * 2 ** a))
    return None

q = urllib.parse.urlencode({"db": "pubmed", "term": TERM, "datetype": "edat", "reldate": days, "retmax": 1000, "retmode": "json"})
raw = get(BASE + "esearch.fcgi?" + q)
if raw is None:
    print(json.dumps({"source": "PubMed", "complete": False, "error": "esearch failed"})); sys.exit(2)
s = json.loads(raw)["esearchresult"]
ids, rows, failed = s.get("idlist", []), [], []
for i in range(0, len(ids), 100):
    time.sleep(0.5)
    x = get(BASE + "efetch.fcgi?" + urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids[i:i + 100]), "retmode": "xml"}))
    if x is None:
        failed.append(i); continue
    for art in ET.fromstring(x).iter("PubmedArticle"):
        mc = art.find("MedlineCitation"); a = mc.find("Article")
        doi = next((e.text for e in art.iter("ArticleId") if e.get("IdType") == "doi"), None)
        pmc = next((e.text for e in art.iter("ArticleId") if e.get("IdType") == "pmc"), None)
        rows.append({"pmid": mc.findtext("PMID"), "title": " ".join("".join(a.find("ArticleTitle").itertext()).split()),
                     "journal": a.findtext("Journal/Title"), "doi": doi, "pmc": pmc,
                     "pubtypes": [p.text for p in a.iter("PublicationType")],
                     "abstract": " ".join(" ".join("".join(t.itertext()) for t in a.iter("AbstractText")).split())})
json.dump(rows, open(out, "w"), ensure_ascii=False)
summary = {"source": "PubMed", "days": days, "hits": int(s.get("count", 0)), "fetched": len(rows), "failed_batches": failed,
           "complete": not failed and len(rows) >= min(len(ids), int(s.get("count", 0)))}
print(json.dumps(summary, ensure_ascii=False))
sys.exit(0 if summary["complete"] else 2)
