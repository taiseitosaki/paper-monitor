"""Convert an arXiv LaTeXML HTML paper into section-aware text chunks for the in-page chat.
usage: html_chunks.py <html> <id_prefix> <out.json> <meta.json>
meta.json: {"doc_default": "main", "appendix_doc": "appendix", "pages": {"section prefix": "page"}}"""
import sys, json, re
from bs4 import BeautifulSoup
src, prefix, out, metaf = sys.argv[1:5]
meta = json.load(open(metaf))
soup = BeautifulSoup(open(src, encoding='utf8').read(), 'html.parser')
for m in soup.select('math'):
    m.replace_with(' ' + (m.get('alttext') or m.get_text(' ')) + ' ')
art = soup.select_one('article') or soup
T = lambda el: re.sub(r'\s+', ' ', el.get_text(' ')).strip()
blocks, sec, para, in_app = [], 'Abstract', '', False
for el in art.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table', 'figcaption', 'div', 'li']):
    cls = el.get('class', [])
    if el.name.startswith('h') and 'ltx_title' in cls:
        t = T(el)
        if any(c in cls for c in ('ltx_title_paragraph','ltx_title_theorem','ltx_title_proof','ltx_runin')): para = t.rstrip(' .'); continue
        if 'ltx_title_appendix' in cls: in_app = True
        if 'ltx_title_bibliography' in cls: t = 'References'
        if 'ltx_title_document' in cls: continue
        sec, para = t, ''; continue
    name = sec + (' / ' + para if para else '')
    doc = 'refs' if sec == 'References' else (meta['appendix_doc'] if in_app else meta['doc_default'])
    if el.name == 'p' and not el.find_parent(['table', 'figcaption', 'li']):
        if el.find_parent('div', class_='ltx_listing'): continue
        t = T(el); t and blocks.append((doc, name, t))
    elif el.name == 'li' and 'ltx_bibitem' in cls:
        blocks.append((doc, name, T(el)))
    elif el.name == 'li' and not el.find_parent(['table', 'figcaption', 'li']):
        t = T(el); t and blocks.append((doc, name, '• ' + t))  # bulleted / enumerated list items (outermost only)
    elif el.name == 'figcaption':
        blocks.append((doc, name, '[CAPTION] ' + T(el)))
    elif el.name == 'table' and 'ltx_tabular' in cls and not el.find_parent('table'):
        rows = [' | '.join(T(c) for c in r.find_all(['td', 'th'])) for r in el.find_all('tr')]
        blocks.append((doc, name, '[TABLE]\n' + '\n'.join(r for r in rows if r.strip(' |'))))
    elif el.name == 'div' and 'ltx_listing' in cls:
        blocks.append((doc, name, '[ALGORITHM]\n' + '\n'.join(T(l) for l in el.select('div.ltx_listingline'))))
def page_for(s):
    best = None
    for k, v in meta['pages'].items():
        if s.startswith(k) and (best is None or len(k) > len(best[0])): best = (k, v)
    return best[1] if best else None
chunks, buf, key, seen = [], [], None, set()
def flush():
    global buf
    if buf:
        d, s = key
        chunks.append({'id': f'{prefix}-{len(chunks)+1:03d}', 'doc': d, 'section': s, 'page': page_for(s), 'text': '\n'.join(buf)}); buf = []
for d, s, t in blocks:
    if t in seen: continue
    seen.add(t)
    top = s.split(' / ')[0]
    if key is None or (d, top) != (key[0], key[1].split(' / ')[0]): flush(); key = (d, s)
    if sum(len(b) for b in buf) + len(t) > 2400:
        carry = [b for b in buf[-2:] if b.startswith('[CAPTION]')] if t.startswith('[TABLE]') else []
        if carry: buf = buf[:len(buf)-len(carry)]
        flush(); key = (d, s); buf.extend(carry)
    buf.append(t if ' / ' not in s or s == key[1] else f'[{s.split(" / ")[1]}] ' + t)
flush()
json.dump(chunks, open(out, 'w'), ensure_ascii=False)
print(len(chunks), 'chunks', sum(len(c['text']) for c in chunks), 'chars')
for c in chunks: print(c['id'], c['doc'], c['page'], '|', c['section'][:70], len(c['text']))
