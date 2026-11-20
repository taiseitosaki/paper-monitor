"""Ranked search across the discussion corpus built by build_corpus.py (spec §4.7).
usage: python3 -I corpus_search.py <corpus_dir> "query words" [--paper P ...] [--kind original|related|notes|explainer|memo ...] [-k 12] [--per-paper 3]
       python3 -I corpus_search.py <corpus_dir> --show KEY [KEY ...]      (KEY = "<No>:<chunk id>", e.g. 012:smith-014)
       python3 -I corpus_search.py <corpus_dir> --check TSV               (a copy of checklist.tsv: every paper's row present with 判定 filled; exit 1 otherwise)
--paper matches the No. (012), the folder name or the paper_id (substring, case-insensitive). BM25 over words (CJK as bigrams).
--per-paper caps hits per paper so that a cross-paper question sees many papers (0 = no cap)."""
import argparse, json, math, re, sys
from collections import Counter, defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("corpus")
ap.add_argument("query", nargs="?", default="")
ap.add_argument("--paper", action="append", default=[])
ap.add_argument("--kind", action="append", default=[])
ap.add_argument("-k", type=int, default=12)
ap.add_argument("--per-paper", type=int, default=3)
ap.add_argument("--show", nargs="+")
ap.add_argument("--check")
a = ap.parse_args()

if a.check:
    import csv
    allp = {r["No"]: r["folder"] for r in csv.DictReader(open(f"{a.corpus}/checklist.tsv", encoding="utf8"), delimiter="\t")}
    got = {r.get("No", "").strip(): r for r in csv.DictReader(open(a.check, encoding="utf8"), delimiter="\t")}
    missing = [f"{n} {f}" for n, f in allp.items() if n not in got]
    empty = [f"{n} {allp[n]}" for n in allp if n in got and not (got[n].get("判定") or "").strip()]
    print(f"全 {len(allp)} 本中 判定済み {len(allp) - len(missing) - len(empty)} 本 / 行なし {len(missing)} 本 / 判定が空 {len(empty)} 本")
    for x in missing:
        print("  行なし:", x)
    for x in empty:
        print("  判定が空:", x)
    sys.exit(1 if missing or empty else 0)

rows = [json.loads(l) for l in open(f"{a.corpus}/chunks.jsonl", encoding="utf8")]
if a.show:
    by = {r["key"]: r for r in rows}
    for k in a.show:
        r = by.get(k)
        print(f"=== {k} [{r['folder']} · {r['doc']} · {r.get('section')} · p.{r.get('page')}]\n{r['text']}\n" if r else f"=== {k}: not found\n")
    sys.exit(0)

STOP = set("the a an of and or to in on for with by is are was were be as at from that this these those it its we our their which using use used".split())


def toks(s):
    s = s.lower()
    out = [w for w in re.findall(r"[a-z0-9]+(?:[-.][a-z0-9]+)*", s) if w not in STOP]
    for run in re.findall(r"[぀-ヿ㐀-鿿]+", s):
        out += [run[i:i + 2] for i in range(max(1, len(run) - 1))]
    return out


def keep(r):
    if a.kind and r["kind"] not in a.kind:
        return False
    if a.paper:
        hay = (r["folder"] + " " + r["paper_id"]).lower()
        return any(p.lower() in hay for p in a.paper)
    return True


rows = [r for r in rows if keep(r)]
q = toks(a.query)
if not q:
    sys.exit("empty query")
docs = [Counter(toks((r.get("section") or "") + " " + r["text"])) for r in rows]
N = len(docs) or 1
avg = sum(sum(d.values()) for d in docs) / N
df = Counter(t for d in docs for t in set(d))
scores = []
for r, d in zip(rows, docs):
    L = sum(d.values()) or 1
    s = sum(math.log(1 + (N - df[t] + 0.5) / (df[t] + 0.5)) * d[t] * 2.2 / (d[t] + 1.2 * (0.25 + 0.75 * L / avg)) for t in set(q) if d[t])
    if s > 0:
        scores.append((s, r))
scores.sort(key=lambda x: -x[0])
seen, shown = defaultdict(int), 0
for s, r in scores:
    if a.per_paper and seen[r["folder"]] >= a.per_paper:
        continue
    seen[r["folder"]] += 1
    t = r["text"]
    m = min((t.lower().find(w) for w in set(q) if t.lower().find(w) >= 0), default=0)
    snip = re.sub(r"\s+", " ", t[max(0, m - 120): m + 280])
    print(f"{s:6.2f}  {r['key']}  [{r['folder']} · {r['doc']} · {str(r.get('section'))[:60]} · p.{r.get('page')}]\n        …{snip}…")
    shown += 1
    if shown >= a.k:
        break
print(f"\n{shown} hits shown / {len(scores)} matching chunks in {len(set(r['folder'] for _, r in scores))} papers")
