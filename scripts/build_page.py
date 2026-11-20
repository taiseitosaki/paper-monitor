"""Assemble an explainer page from the library template.
usage: python3 -I build_page.py <paper_dir> <title> <examples.json> [template.html] [--config topic.json]
Reads <paper_dir>/article.html, writes <paper_dir>/index.html and _test.html (charset-prefixed, for local QA).
The template defaults to ../templates/paper-template.html relative to this script (keep the library's folder layout).
{{LIBRARY_NAME}} / {{LIBRARY_URL}} / {{FIELD}} / {{EXAMPLE_QUESTION}} are filled from the theme config.
Raw '<' / '>' inside \\( \\) and \\[ \\] math are escaped so the browser does not read them as HTML tags."""
import os, re, json, sys

def topic_config():
    """Theme settings: --config PATH, else $TOPIC_CONFIG, else ../config/topic.json next to this script."""
    p = None
    if "--config" in sys.argv:
        i = sys.argv.index("--config"); p = sys.argv[i + 1]; del sys.argv[i:i + 2]
    p = p or os.environ.get("TOPIC_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "topic.json")
    return json.load(open(p, encoding="utf8"))


cfg = topic_config()
if not cfg.get("library_url"):
    sys.exit("config: library_url is empty (publish the library first and write its URL into config/topic.json)")

d, title, exf = sys.argv[1:4]
tpl = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "paper-template.html")
t = open(tpl, encoding="utf8").read()
a = open(f"{d}/article.html", encoding="utf8").read()
ex = json.load(open(exf, encoding="utf8"))

def esc_math(m):
    return m.group(0).replace("<", "&lt;").replace(">", "&gt;")
a, n_math = re.subn(r"\\\((.*?)\\\)|\\\[(.*?)\\\]", lambda m: esc_math(m) if ("<" in m.group(0) or ">" in m.group(0)) else m.group(0), a, flags=re.S)

t = re.sub(r"<!--\s*Research Library — 論文解説ページ テンプレート.*?-->\n", "", t, flags=re.S)
t = t.replace("<title>【短い論文名】 解説</title>", f"<title>{title}</title>")
for k, v in {"LIBRARY_NAME": cfg["short_name"], "LIBRARY_URL": cfg["library_url"], "FIELD": cfg["field_ja"],
             "EXAMPLE_QUESTION": cfg.get("chat_example_question", "")}.items():
    t = t.replace("{{" + k + "}}", v)
t = re.sub(r'<article id="explainer">.*?</article>', lambda m: a.strip(), t, flags=re.S)
t = re.sub(r"const EXAMPLES = \[.*?\];", lambda m: "const EXAMPLES = " + json.dumps(ex, ensure_ascii=False, indent=2) + ";", t, flags=re.S)
left = [m.start() for m in re.finditer("【", t)]
assert not left, ("unfilled placeholders", [t[i:i + 40] for i in left[:5]])
open(f"{d}/index.html", "w", encoding="utf8").write(t)
open(f"{d}/_test.html", "w", encoding="utf8").write('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' + t)
print("built", len(t.encode()), "bytes;", n_math, "math spans checked")
