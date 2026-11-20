"""Lay out the whole library as a corpus for a cross-paper discussion session (spec §4.7).
usage: python3 -I build_corpus.py <work_dir> [--config topic.json]
Inputs (same layout as export_zip.py):
  <work_dir>/db/<collection>/<doc_id>.json   database documents (ArtifactData out_dir): papers, digests
  <work_dir>/raw/<artifact id>/              each explainer's and digest's published files (id = last URL segment)
  <work_dir>/expected.json                   {"<artifact id>": ["index.html", "source/chunks.json", ...]} from the file listings
  <work_dir>/memos/<artifact id>.json         user memos = comment threads NOT sent to Claude (spec §6.3, §4.7):
                                             [{thread_id, location, quote, resolved, created, comments: [{at, text}]}]; [] when none.
                                             Optional: a missing file is reported in the summary (memo_files_missing), not an error.
Writes <work_dir>/corpus/ (README.md, PAPERS.md, MY_MEMOS.md, ledger.tsv, chunks.jsonl, papers/<NNN>_<name>/ incl. memos.md, digests/) and prints a JSON summary.
Exit code 0 = everything present, 2 = files missing (nothing is written)."""
import csv, glob, html, json, os, re, shutil, sys

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


cfg = topic_config()
CATS = cfg.get("categories", {})
CAT_NOTE = "・".join(f"{k} {v}" for k, v in CATS.items())

work = os.path.abspath(sys.argv[1])
out = f"{work}/corpus"


def load(path):
    d = json.load(open(path, encoding="utf8"))
    return d.get("data", d) if isinstance(d, dict) else d


def slug(url):
    return (url or "").split("#")[0].rstrip("/").rsplit("/", 1)[-1]


def safe(s, n=48):
    s = re.sub(r"[^A-Za-z0-9 ._()+-]+", " ", s or "").strip()
    return re.sub(r"\s+", "_", s)[:n].rstrip("_.") or "paper"


def short(title):
    t = re.sub(r"\s*\(arXiv[^)]*\)\s*$", "", title or "")
    head = re.split(r"\s*[:—–]\s+", t, maxsplit=1)[0]
    return head if 3 <= len(head) <= 48 else t[:48]


def to_text(fragment):
    s = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", fragment)
    s = re.sub(r"<img[^>]*alt=\"([^\"]*)\"[^>]*>", r" [図: \1] ", s)
    s = re.sub(r"<h([1-4])[^>]*>", lambda m: "\n\n" + "#" * (int(m.group(1)) + 1) + " ", s)
    s = re.sub(r"</(p|li|tr|h[1-4]|figcaption|caption|div|blockquote|dd|dt)>|<br\s*/?>", "\n", s)
    s = re.sub(r"<li[^>]*>", "- ", s)
    s = re.sub(r"</t[dh]>", " | ", s)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"[ \t ]+", " ", s)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", "\n".join(l.strip() for l in s.splitlines())).strip()


def explainer_sections(page):
    m = re.search(r'<article id="explainer">([\s\S]*?)</article>', page)
    body = m.group(1) if m else page
    secs = re.findall(r'<section id="([\w-]+)"[^>]*>([\s\S]*?)</section>', body)
    return [(sid, to_text(h)) for sid, h in secs if sid not in ("chat", "feedback")] or [("page", to_text(body))]


def kind(doc):
    d = (doc or "").split(" ")[0]
    if d in ("main", "appendix", "supp", "refs"):
        return "original"
    if d.startswith(("prior:", "followup:")):
        return "related"
    if d in ("figure-notes", "verification"):
        return "notes"
    return "original"


papers = []
for f in sorted(glob.glob(f"{work}/db/papers/*.json")):
    p = load(f)
    p["_id"] = os.path.basename(f)[:-5]
    papers.append(p)
digests = {os.path.basename(f)[:-5]: load(f) for f in sorted(glob.glob(f"{work}/db/digests/*.json"))}
expl = sorted((p for p in papers if p.get("explainer_url")), key=lambda p: (p.get("first_published") or "", p["_id"]))

expected = json.load(open(f"{work}/expected.json", encoding="utf8")) if os.path.exists(f"{work}/expected.json") else {}
need = {slug(p["explainer_url"]): ["index.html", "source/chunks.json", "source/manifest.json"] for p in expl}
need.update({slug(d["url"]): ["index.html"] for d in digests.values() if d.get("url")})
missing = [f"{k}/{x}" for k, xs in need.items() for x in sorted(set(xs) | set(expected.get(k, []))) if not os.path.isfile(f"{work}/raw/{k}/{x}")]
if missing or not papers:
    print(json.dumps({"complete": False, "papers": len(papers), "missing": missing[:80]}, ensure_ascii=False))
    sys.exit(2)

shutil.rmtree(out, ignore_errors=True)
os.makedirs(f"{out}/papers")
os.makedirs(f"{out}/digests")
jl = open(f"{out}/chunks.jsonl", "w", encoding="utf8")
rows, n_chunks, folder_of = [], 0, {}
memo_count, memo_missing, all_memos = {}, [], []
MEMONOTE = "利用者メモ（解説ページのコメントのうち Claude に送られていないもの。利用者が解説を読みながら付けた見解・疑問で、原著でも二次資料でもない。根拠にしない）"
DOCNOTE = {"original": "原著（本文・付録・補足資料・参考文献）", "related": "解説作成時に収録した先行研究・後続論文の全文または関連箇所（prior: / followup:）",
           "notes": "解説作成者のメモ（図表の目視記録・独立検証の記録）。原著の一部ではない"}

for i, p in enumerate(expl, 1):
    s = slug(p["explainer_url"])
    folder = f"{i:03d}_{safe(short(p.get('title')))}"
    folder_of[p["_id"]] = folder
    d = f"{out}/papers/{folder}"
    os.makedirs(d)
    raw = f"{work}/raw/{s}"
    chunks = json.load(open(f"{raw}/source/chunks.json", encoding="utf8"))
    man = json.load(open(f"{raw}/source/manifest.json", encoding="utf8"))
    shutil.copy(f"{raw}/source/manifest.json", f"{d}/manifest.json")
    if os.path.isdir(f"{raw}/figs"):
        shutil.copytree(f"{raw}/figs", f"{d}/figs")
    head = (f"# {p.get('title')}\n\npaper_id: {p['_id']} ・ 公開 {p.get('first_published') or '?'} ・ 関連度 {p.get('relevance') or '?'} ・ "
            f"解説 {p['explainer_url']}\n")
    files = {k: [head + f"\n資料の種類: {v}\n参照キーは `{folder[:3]}:<chunk id>`（corpus_search.py --show で全文表示）\n"] for k, v in DOCNOTE.items()}
    cur = {}
    for c in chunks:
        k = kind(c.get("doc"))
        if cur.get(k) != c.get("doc"):
            cur[k] = c.get("doc")
            files[k].append(f"\n\n## [{cur[k]}]\n")
        pg = f" · p.{c['page']}" if c.get("page") not in (None, "") else ""
        files[k].append(f"\n### [{c.get('id')}] {c.get('doc')} · {c.get('section') or ''}{pg}\n\n{c.get('text') or ''}\n")
        jl.write(json.dumps({"key": f"{folder[:3]}:{c.get('id')}", "folder": folder, "paper_id": p["_id"], "kind": k, **c}, ensure_ascii=False) + "\n")
        n_chunks += 1
    for k, parts in files.items():
        if len(parts) > 1:
            open(f"{d}/{k}.md", "w", encoding="utf8").write("".join(parts))
    page = open(f"{raw}/index.html", encoding="utf8").read()
    ex = [head + "\n資料の種類: 日本語解説（二次資料。主張の根拠は原著側で確かめる）\n"]
    for sid, txt in explainer_sections(page):
        ex.append(f"\n\n## [explainer-{sid}]\n\n{txt}\n")
        jl.write(json.dumps({"key": f"{folder[:3]}:explainer-{sid}", "folder": folder, "paper_id": p["_id"], "kind": "explainer",
                             "id": f"explainer-{sid}", "doc": "explainer", "section": sid, "page": None, "text": txt}, ensure_ascii=False) + "\n")
        n_chunks += 1
    open(f"{d}/explainer.md", "w", encoding="utf8").write("".join(ex))
    mp = f"{work}/memos/{s}.json"
    memos = load(mp) if os.path.exists(mp) else None
    if memos is None:
        memo_missing.append(s)
    memos = [m for m in (memos or []) if any((c.get("text") or "").strip() for c in (m.get("comments") or []))]
    memo_count[p["_id"]] = len(memos)
    if memos:
        mm = []
        for j, m in enumerate(memos, 1):
            loc, q = (m.get("location") or "").strip(), (m.get("quote") or "").strip()
            body = "\n".join(f"- [{c.get('at') or ''}] {c.get('text') or ''}".strip() for c in (m.get("comments") or []))
            quote = ("> " + q.replace("\n", "\n> ") + "\n\n") if q else ""
            mm.append(f"\n\n## [memo-{j}] {loc or '（位置なし）'}{' ・ 解決済み' if m.get('resolved') else ''} ・ {m.get('created') or ''}\n\n{quote}{body}\n")
            jl.write(json.dumps({"key": f"{folder[:3]}:memo-{j}", "folder": folder, "paper_id": p["_id"], "kind": "memo", "id": f"memo-{j}",
                                 "doc": "memo", "section": loc, "page": None, "thread_id": m.get("thread_id"),
                                 "text": (f"引用: {q}\n" if q else "") + body}, ensure_ascii=False) + "\n")
            n_chunks += 1
        open(f"{d}/memos.md", "w", encoding="utf8").write(head + f"\n資料の種類: {MEMONOTE}\n参照キーは `{folder[:3]}:memo-<n>`\n" + "".join(mm))
        all_memos.append((folder, p, mm))
    docs = "; ".join(f"{x.get('doc')}: {x.get('title', '')}" for x in man.get("documents", []))
    rows.append((p, folder, docs, "; ".join(man.get("missing", []) or [])))
jl.close()

for wk, dg in sorted(digests.items()):
    if dg.get("url"):
        page = open(f"{work}/raw/{slug(dg['url'])}/index.html", encoding="utf8").read()
        open(f"{out}/digests/{wk}.md", "w", encoding="utf8").write(f"# Weekly Digest {wk}（{dg.get('week_start', '')} 〜 {dg.get('week_end', '')}）\n\n{dg['url']}\n\n{to_text(page)}\n")

with open(f"{out}/MY_MEMOS.md", "w", encoding="utf8") as w:
    w.write(f"# 利用者メモ（{sum(memo_count.values())} 件、{len(all_memos)} 本）\n\n資料の種類: {MEMONOTE}\n"
            "参照キーは `<No>:memo-<n>`。各メモの見出しは「解説ページ上の位置（節）・解決済みかどうか・作成日」、`>` は利用者が選んだ解説の文。\n")
    if memo_missing:
        w.write(f"\n注意: 次の {len(memo_missing)} 本はメモを取得できていない（memos/ にファイルなし）: {', '.join(memo_missing)}\n")
    for folder, p, mm in all_memos:
        w.write(f"\n\n# {folder} {p.get('title')}\n\n解説 {p['explainer_url']}\n" + "".join(x.replace("\n## [memo-", f"\n## [{folder[:3]}:memo-") for x in mm))

cell = lambda s: re.sub(r"\s+", " ", str(s or "")).replace("|", "/")
with open(f"{out}/PAPERS.md", "w", encoding="utf8") as w:
    w.write(f"# 全文を収録した論文（{len(rows)} 本）\n\nNo. は参照キーの先頭3桁と papers/ のフォルダ名に対応する。分類: {CAT_NOTE}。\n\n")
    w.write("| No. | フォルダ | 論文 | 公開 | 関連度 | 分類 | 種別 | 利用者メモ | 解説 |\n|---|---|---|---|---|---|---|---|---|\n")
    for p, folder, _, _ in rows:
        w.write(f"| {folder[:3]} | {folder} | {cell(p.get('title'))} | {cell(p.get('first_published'))} | {cell(p.get('relevance'))} | "
                f"{' '.join(c for c in (p.get('categories') or []) if c in CATS)} | {cell(p.get('origin'))} | {memo_count.get(p['_id'], 0)} | {p['explainer_url']} |\n")
    w.write("\n# 各論文の収録資料と未取得資料（manifest より）\n")
    for p, folder, docs, miss in rows:
        w.write(f"\n## {folder}\n\n- 収録: {cell(docs)}\n- 未取得: {cell(miss) or 'なし'}\n")

with open(f"{out}/checklist.tsv", "w", newline="", encoding="utf8") as w:
    wr = csv.writer(w, delimiter="\t")
    wr.writerow(["No", "folder", "title", "判定", "根拠キー", "メモ"])
    for p, folder, _, _ in rows:
        wr.writerow([folder[:3], folder, cell(p.get("title")), "", "", ""])

cols = ["_id", "title", "first_published", "relevance", "status", "categories", "origin", "peer_review", "venue", "url", "relevance_note", "corpus_folder"]
with open(f"{out}/ledger.tsv", "w", newline="", encoding="utf8") as w:
    wr = csv.writer(w, delimiter="\t")
    wr.writerow(cols)
    for p in sorted(papers, key=lambda p: p.get("first_published") or ""):
        wr.writerow([folder_of.get(p["_id"], "") if c == "corpus_folder" else " ".join(p.get(c) or []) if c == "categories" else cell(p.get(c)) for c in cols])

open(f"{out}/README.md", "w", encoding="utf8").write(f"""# {cfg["library_name"]} — 議論用コーパス

- PAPERS.md: 全文を収録した論文 {len(rows)} 本の一覧（No.・フォルダ・関連度・分類）と、各論文の収録資料・未取得資料
- ledger.tsv: 論文台帳の全 {len(papers)} 件（解説のない {len(papers) - len(rows)} 件は書誌・関連度メモのみ。本文は収録していない）
- papers/<No>_<名前>/original.md: 原著（本文・付録・補足資料・参考文献）。見出し `### [chunk id] doc · 節 · p.ページ`
- papers/<No>_<名前>/related.md: 解説作成時に収録した先行研究・後続論文（prior: / followup:）
- papers/<No>_<名前>/notes.md: 解説作成者の図表メモ・独立検証メモ（原著ではない）
- papers/<No>_<名前>/explainer.md: 日本語解説（二次資料）
- papers/<No>_<名前>/memos.md と MY_MEMOS.md: 利用者メモ（{sum(memo_count.values())} 件。解説ページのコメントのうち Claude に送られていないもの。利用者の見解・疑問で、根拠にしない。引用時は「利用者メモ」と明記）
- papers/<No>_<名前>/figs/: 図表画像、manifest.json: 収録資料・図表・ライセンス
- digests/: Weekly Digest
- checklist.tsv: 全文収録の全論文を1行ずつ並べた確認表のひな形（論文横断の質問ではコピーして全行の「判定」を埋める）
- chunks.jsonl: 全チャンク（{n_chunks} 件）。参照キー key = "<No>:<chunk id>"

検索: `python3 -I scripts/corpus_search.py corpus "query" [--paper 012 --paper Smith] [--kind original] [-k 12] [--per-paper 3]`
全文表示: `python3 -I scripts/corpus_search.py corpus --show 012:smith-014`
全件確認: `python3 -I scripts/corpus_search.py corpus --check work/<名前>.tsv`（全論文の行があり「判定」が空でないかを確かめる）
""")
print(json.dumps({"complete": True, "corpus": out, "papers": len(papers), "explainers": len(rows), "chunks": n_chunks, "digests": len(digests),
                  "memos": sum(memo_count.values()), "memo_files_missing": memo_missing}, ensure_ascii=False))
