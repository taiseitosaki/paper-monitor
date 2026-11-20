"""usage: make_source.py <paper_dir> <extra.json>
extra.json: {"prior": [[prefix_dir, doc_name]...], "notes": [[section, text]...], "verify": [[section, text]...], "manifest": {...}}
Combines source/_main.json (+ optional prior chunk files) + notes + verification into source/chunks.json and writes source/manifest.json."""
import json, sys
d, ef = sys.argv[1:3]
e = json.load(open(ef, encoding='utf8'))
chunks = json.load(open(f'{d}/source/_main.json'))
for path, docname in e.get('prior', []):
    for c in json.load(open(path)):
        c['doc'] = docname + (' refs' if c['doc'] == 'refs' else (' appendix' if c['doc'] == 'appendix' else ''))
        chunks.append(c)
for i, (s, t) in enumerate(e.get('notes', [])):
    chunks.append({"id": f"fignote-{i+1:02d}", "doc": "figure-notes", "section": s, "page": None, "text": "[Visual check by explainer author; not part of the original paper] " + t})
for i, (s, t) in enumerate(e.get('verify', [])):
    chunks.append({"id": f"verify-{i+1:02d}", "doc": "verification", "section": s, "page": None, "text": "[Independent verification notes by explainer author; not part of the original paper] " + t})
json.dump(chunks, open(f'{d}/source/chunks.json', 'w'), ensure_ascii=False)
json.dump(e['manifest'], open(f'{d}/source/manifest.json', 'w'), ensure_ascii=False, indent=1)
print(len(chunks), 'chunks', len(json.dumps(chunks, ensure_ascii=False).encode()), 'bytes')
