"""Chunk a PDF's per-page text (pages.txt from pdfplumber with '===== PAGE n =====' markers) by numbered headings.
usage: pdf_chunks.py <pages.txt> <prefix> <out.json> <drop_line_regex> <refs_start_regex>"""
import re, sys, json
src, prefix, out, drop, refs = sys.argv[1:6]
drop_re, refs_re = re.compile(drop), re.compile(refs)
head_re = re.compile(r'^(\d+(\.\d+)*\.?)\s+[A-Z][A-Za-z].{0,80}$')
pages = re.split(r'\n===== PAGE (\d+) =====\n', open(src, encoding='utf8').read())
chunks, buf, sec, doc, start_page = [], [], 'Front matter', 'main', None
def flush(page):
    global buf, start_page
    t = '\n'.join(buf).strip()
    if t:
        pg = str(start_page) if start_page == page else f'{start_page}-{page}'
        chunks.append({'id': f'{prefix}-{len(chunks)+1:03d}', 'doc': doc, 'section': sec, 'page': pg, 'text': t})
    buf, start_page = [], None
last_page = None
for i in range(1, len(pages), 2):
    page = int(pages[i]); lines = [l for l in pages[i+1].split('\n') if not drop_re.search(l)]
    for l in lines:
        s = l.strip()
        if not s: continue
        if refs_re.match(s) and doc != 'refs':
            flush(last_page or page); doc, sec = 'refs', 'References'
        elif doc != 'refs' and head_re.match(s) and len(s) < 90 and not re.match(r'^\d+(\.\d+)?\s+\d', s) and 'License' not in s:
            flush(last_page or page); sec = s
        if start_page is None: start_page = page
        buf.append(s); last_page = page
        if sum(len(b) for b in buf) > 2200: flush(page)
flush(last_page)
json.dump(chunks, open(out, 'w'), ensure_ascii=False)
print(len(chunks), 'chunks'); [print(c['id'], c['doc'], c['page'], c['section'][:60], len(c['text'])) for c in chunks]
