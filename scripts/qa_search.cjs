// usage: node qa_search.cjs <paper_dir> '<json array of [query, doc?]>'
const fs = require('fs'); const d = process.argv[2]; const qs = JSON.parse(process.argv[3]);
const h = fs.readFileSync(d + '/index.html', 'utf8');
let js = h.match(/<script>\n(\/\*[\s\S]*?)<\/script>/)[1].replace('init();', '');
globalThis.document = { querySelector: () => null, querySelectorAll: () => [], title: 't' }; globalThis.window = {};
eval(js + `
const art = fs.readFileSync(d + '/article.html', 'utf8');
const secs = [...art.matchAll(/<section id="(\\w+)">([\\s\\S]*?)<\\/section>/g)].map(m => ({ id: 'explainer-' + m[1], doc: 'explainer', section: m[1], page: null, text: m[2].replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ').slice(0, 9000) }));
S.manifest = JSON.parse(fs.readFileSync(d + '/source/manifest.json', 'utf8'));
S.chunks = JSON.parse(fs.readFileSync(d + '/source/chunks.json', 'utf8')).concat(secs);
S.index = buildIndex(S.chunks);
for (const [q, doc] of qs) console.log('Q:', q, doc || '', '\\n   ' + search(q, { doc, k: 5 }).map(r => r.id + ' [' + r.doc + ' §' + String(r.section).slice(0, 45) + ' p.' + r.page + '] ' + r.score).join('\\n   '));
console.log('chunks', S.chunks.length, 'contents bytes', JSON.stringify(contents()).length);
`);
