#!/bin/bash

real_file=`realpath $0`
bin_dir=`dirname $real_file`
if [ -z "$1" ]; then
    echo "please given dest dir!";
    exit 1
fi

dest=$1

# anchor-right.py needs python2; only run when available (otherwise skip, not fatal)
anchor_right() {
    command -v python2 >/dev/null 2>&1 && $bin_dir/anchor-right.py "$@" || true
}

for p in `find $dest -name '*.org'`; do
    html=${p%.org}.html
    echo "generate $html"
    cat $p | $bin_dir/org2html.py > $html
    anchor_right $html
done

# markdown -> html (uses conda `markdown` module; minimal fallback if unavailable)
py=~/miniconda3/bin/python
if $py -c 'import markdown' 2>/dev/null; then
    md_render() { $py -c 'import sys, markdown; sys.stdout.write(markdown.markdown(open(sys.argv[1]).read()))' "$1"; }
else
    # minimal fallback: covers headings / lists / links / code blocks (index.md subset)
    md_render() { $py - "$1" <<'PYEOF'
import sys, re, html
lines = open(sys.argv[1]).read().split('\n')
out, in_ul, in_code = [], False, False
def flush_ul():
    global in_ul
    if in_ul: out.append('</ul>'); in_ul = False
def md_inline(s):
    s = html.escape(s)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
for ln in lines:
    if ln.startswith('```'):
        flush_ul()
        out.append('</code></pre>' if in_code else '<pre><code>')
        in_code = not in_code
        continue
    if in_code:
        out.append(html.escape(ln)); continue
    m = re.match(r'^(#{1,6})\s+(.*)', ln)
    if m:
        flush_ul(); n = len(m.group(1))
        out.append('<h%d>%s</h%d>' % (n, md_inline(m.group(2)), n)); continue
    m = re.match(r'^[-*+]\s+(.*)', ln)
    if m:
        if not in_ul: out.append('<ul>'); in_ul = True
        out.append('<li>%s</li>' % md_inline(m.group(1))); continue
    flush_ul()
flush_ul()
if in_code: out.append('</code></pre>')
sys.stdout.write('\n'.join(out))
PYEOF
}
fi

# rewrite href="*.org" / "*.md" -> "*.html" (same job as anchor-right.py, py3-safe)
org_links_to_html() {
    $py - "$1" <<'PYEOF'
import sys, re
p = sys.argv[1]
c = open(p).read()
new = re.sub(r'(<a\s+href\s*=\s*"[^"]*?)\.(?:org|md)(")', r'\1.html\2', c)
if new != c:
    open(p, 'w').write(new)
PYEOF
}

for p in `find $dest -name '*.md'`; do
    html=${p%.md}.html
    echo "generate $html"
    title=`basename ${p%.md}`
    { echo "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>$title</title></head><body>"
      md_render $p
      echo "</body></html>"
    } > $html
    org_links_to_html $html
    anchor_right $html
done
