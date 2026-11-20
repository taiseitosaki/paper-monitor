"""Build the whole-library ZIP (spec §4.6) from files a session has already saved locally.
usage: python3 -I export_zip.py <work_dir> [--config topic.json]
<work_dir>/db/<collection>/<doc_id>.json   database documents (ArtifactData out_dir)
<work_dir>/raw/_library/                   the library's published files
<work_dir>/raw/<artifact id>/              each explainer's and digest's published files (id = last URL segment)
<work_dir>/expected.json                   {"<artifact id or _library>": ["index.html", ...]} from the file listings
Writes <work_dir>/<library_name>_<YYYY-MM-DD>.zip and prints a JSON summary.
Exit code 0 = everything present, 2 = files missing (no ZIP is written)."""
import csv, datetime, glob, html, json, os, re, shutil, sys, zipfile

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


cfg = topic_config()
LIB = cfg["library_name"]

work = os.path.abspath(sys.argv[1])
today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
name = re.sub(r"[^A-Za-z0-9]+", "_", LIB).strip("_") or "Research_Library"
out = f"{work}/{name}"
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)


def load(path):
    d = json.load(open(path, encoding="utf8"))
    return d.get("data", d)


def safe(s, n=70):
    s = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", s or "").strip()
    return re.sub(r"\s+", " ", s)[:n].rstrip(" .")


expected = json.load(open(f"{work}/expected.json", encoding="utf8"))
missing = [f"{k}/{p}" for k, ps in expected.items() for p in ps if not os.path.isfile(f"{work}/raw/{k}/{p}")]

papers = []
for f in sorted(glob.glob(f"{work}/db/papers/*.json")):
    p = load(f)
    p["_id"] = os.path.basename(f)[:-5]
    papers.append(p)
digests = {os.path.basename(f)[:-5]: load(f) for f in sorted(glob.glob(f"{work}/db/digests/*.json"))}
expl = sorted((p for p in papers if p.get("explainer_url")), key=lambda p: p.get("first_published") or "")

needed = ["_library"] + [p["explainer_url"].rstrip("/").rsplit("/", 1)[1] for p in expl]
needed += [d["url"].rstrip("/").rsplit("/", 1)[1] for d in digests.values() if d.get("url")]
missing += [k for k in needed if k not in expected]
if missing or not papers:
    print(json.dumps({"complete": False, "papers": len(papers), "missing": missing[:50]}, ensure_ascii=False))
    sys.exit(2)

shutil.copytree(f"{work}/raw/_library", f"{out}/01_library")
shutil.copytree(f"{work}/db", f"{out}/04_database")

rows = []
for i, p in enumerate(expl, 1):
    slug = p["explainer_url"].rstrip("/").rsplit("/", 1)[1]
    folder = f"{i:03d}_{safe(p.get('title'))}"
    shutil.copytree(f"{work}/raw/{slug}", f"{out}/02_explainers/{folder}")
    chunks = json.load(open(f"{work}/raw/{slug}/source/chunks.json", encoding="utf8"))
    with open(f"{out}/02_explainers/{folder}/source/fulltext.md", "w", encoding="utf8") as w:
        w.write(f"# {p.get('title')}\n\n")
        cur = None
        for c in chunks:
            if c.get("doc") != cur:
                cur = c.get("doc")
                w.write(f"\n\n# [{cur}]\n")
            pg = f" (p.{c['page']})" if c.get("page") else ""
            w.write(f"\n## {c.get('section') or ''}{pg}\n\n{c.get('text') or ''}\n")
    rows.append((p, folder))

os.makedirs(f"{out}/03_digests", exist_ok=True)
for wk, d in digests.items():
    if d.get("url"):
        shutil.copy(f"{work}/raw/{d['url'].rstrip('/').rsplit('/', 1)[1]}/index.html", f"{out}/03_digests/{wk}.html")

cols = ["_id", "title", "authors", "first_published", "last_checked", "peer_review", "venue", "relevance", "status",
        "origin", "url", "explainer_url", "pdf", "html", "supplement", "code", "relevance_note", "status_note"]
with open(f"{out}/papers_ledger.csv", "w", newline="", encoding="utf-8-sig") as w:
    wr = csv.writer(w)
    wr.writerow(cols)
    for p in papers:
        sl = p.get("source_links") or {}
        wr.writerow([", ".join(p.get("authors") or []) if c == "authors" else (sl.get(c) or "") if c in ("pdf", "html", "supplement", "code") else p.get(c, "") for c in cols])

links = [[p["_id"], (p.get("source_links") or {})["pdf"]] for p in papers if (p.get("source_links") or {}).get("pdf")]
with open(f"{out}/download_original_pdfs.py", "w", encoding="utf8") as w:
    w.write('"""Download the original PDFs linked in the ledger into ./05_original_pdfs. Run on your own computer: python3 download_original_pdfs.py\n'
            'Some publishers may refuse scripted downloads, and some links are not PDFs; open the failed links in a browser."""\n')
    w.write("import os, re, time, urllib.request\nLINKS = " + json.dumps(links, ensure_ascii=False, indent=1) + "\n")
    w.write('''os.makedirs("05_original_pdfs", exist_ok=True)
failed = []
for pid, url in LINKS:
    path = os.path.join("05_original_pdfs", re.sub(r"[^A-Za-z0-9._-]", "_", pid) + ".pdf")
    if os.path.exists(path):
        continue
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=120).read()
        if data[:4] != b"%PDF":
            raise ValueError("not a PDF (likely an HTML page)")
        open(path, "wb").write(data)
        print("ok", pid)
    except Exception as e:
        failed.append((pid, url, str(e)))
        print("FAILED", pid, e)
    time.sleep(3)
print(len(LINKS) - len(failed), "of", len(LINKS), "done")
for f in failed:
    print(f)
''')

esc = lambda s: html.escape(s or "", quote=True)
items = "\n".join(
    f'<li><a href="02_explainers/{esc(fd)}/index.html">{esc(p.get("title"))}</a> '
    f'<small>{esc(p.get("first_published"))} · <a href="02_explainers/{esc(fd)}/source/fulltext.md">原著テキスト</a></small></li>'
    for p, fd in rows)
open(f"{out}/index.html", "w", encoding="utf8").write(
    f'<!doctype html><meta charset="utf-8"><title>{html.escape(LIB)} Export</title>'
    '<style>body{font:15px/1.7 system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 16px}small{color:#667}</style>'
    f'<h1>{html.escape(LIB)}（{today} の書き出し）</h1><ul>{items}</ul>')

open(f"{out}/README.md", "w", encoding="utf8").write(f"""# {LIB} 書き出し

書き出し日: {today}（JST）

- index.html: 解説{len(rows)}本の一覧（ここから開く）
- papers_ledger.csv: 論文台帳{len(papers)}件（Excel で開けます）
- 01_library/: ライブラリ本体、運用仕様書、テンプレート、スクリプト
- 02_explainers/: 論文ごとの解説ページ（index.html）、図表（figs/）、原著の全文テキスト（source/chunks.json、読みやすい形の source/fulltext.md）、資料一覧（source/manifest.json）
- 03_digests/: Weekly Digest
- 04_database/: ライブラリのデータベース全件（JSON）
- download_original_pdfs.py: 原著 PDF を自分の PC に取得するスクリプト

## 注意

- 原著 PDF そのものは含みません。ライブラリには PDF が保存されておらず、外部サイトへのリンクだけです。
- 解説がある論文の本文は source/ のテキストに入っています。解説がない{len(papers) - len(rows)}件は、台帳の情報とリンクのみです。
- 解説ページの数式、フォント、ページ内チャットは claude.ai での表示を前提にしています。ローカルではチャットは動かず、数式の表示にはネット接続が必要な場合があります。
- コメントのスレッドは含みません。
- 原著のライセンスは論文ごとに異なります。再配布の前に各 manifest.json のライセンス表記を確認してください。
""")

zp = f"{work}/{name}_{today}.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(out):
        for f in files:
            full = os.path.join(root, f)
            z.write(full, os.path.relpath(full, work))
assert zipfile.ZipFile(zp).testzip() is None
n = sum(len(fs) for _, _, fs in os.walk(out))
print(json.dumps({"complete": True, "zip": zp, "size_mb": round(os.path.getsize(zp) / 1e6, 1), "files": n, "papers": len(papers),
                  "explainers": len(rows), "digests": len(digests), "pdf_links": len(links)}, ensure_ascii=False))
