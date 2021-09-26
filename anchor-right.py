#!/usr/bin/env python2
'''
./anchor-right.py html1 html2...
'''
import sys
import re

def resolve_anchor_ref(content, new_anchor):
    def anchor_sub(m):
        return '<a href="%s" %s>'%(new_anchor(m.group(1)), m.group(2))
    return re.sub('<a\s+href\s*=\s*"(.*?)"(.*?)>', anchor_sub, content)
def new_anchor(a):
    return re.sub('[.]org$', '.html', a)

def anchor_right(p):
    with open(p) as f:
        c = f.read()
    new_html = resolve_anchor_ref(c, new_anchor)
    if c == new_html:
        print '%s not change'%(p)
    else:
        with open(p, 'w') as f:
            f.write(new_html)
        print '%s changed'%(p)

def help(): print __doc__
len(sys.argv) > 1 or help() or sys.exit(1)
for i in sys.argv[1:]:
    anchor_right(i)
