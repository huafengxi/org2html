#!/usr/bin/env python2
# -*- coding: utf-8 -*-
'''
Usage:
cat a.org | ./org2html.py
'''
import sys
import re
import pprint
import itertools
import string
import cgi

indent_spec_str = '''
head,	-10,	^([*]+)
list,	+1,	[0-9]+[.]
ulist,	+1,	[+]
table,	1024,	[|].*[|]$
code,	0,	:
par,	128,	$
text,	0,	
'''
indent_spec = [(name, int(base_indent), rexp) for name, base_indent, rexp in re.findall('\n([^,]+),\t([^,]+),\t(.*?)$', indent_spec_str, re.M)]

def get_indent(line):
    '''line -> name, indent'''
    for name, base_indent, rexp, in indent_spec:
        m = re.match("^( *)" + rexp, line)
        if not m: continue
        indent = base_indent + len(m.group(1))
        if len(m.groups()) > 1:
            indent += len(m.group(2))
        return name, indent
    raise Exception("not matched by any spec: %s"%(line))

def parse_indent(s):
    root = [-128, 'root']
    stack = [root]
    for line in s.split('\n'):
        name, indent = get_indent(line)
        while indent <= stack[-1][0]:
            stack.pop()
        if indent > stack[-1][0]:
            new_top = [indent, name]
            stack[-1].append(new_top)
            stack.append(new_top)
        stack[-1].append(line)
    return root

def remove_indent(tree):
    if type(tree) != list: return tree
    return [remove_indent(item) for item in tree[1:]]

def aggregate_group(tree):
    if type(tree) != list: return tree
    return [tree[0]] + [[gkey + '+'] + [aggregate_group(item) for item in group] for gkey, group in itertools.groupby(tree[1:], lambda x: type(x) == list and x[0] or 'leaf')]

css_str = '''
body {
    //font-size: 16px;
    margin:0px 5px 0px 5px;
}
a { text-decoration: none; }
.section-number { padding-right: 10px; }
h1,h2,h3,h4,h5 {};
th { background: black; color: white; }
th, td {  vertical-align: middle; text-align:left;  font-family: courier, monospace;}
table, th, td { border: 1px solid black; border-collapse: collapse; }
code, pre {
  padding: 0 3px 2px;
  border-radius: 3px;
  font-family: courier,monospace;
}

nav {
    padding: 1px;
    margin-bottom: 1px;
    /* background: DarkSlateGray; */
}
nav a {
    color: Gray;
    padding: 3px;
}

'''
html_template_str = '''
root: <html><head><title>$title</title><meta charset="UTF-8"/><style type="text/css">$css</style></head><body><div>$html_header</div><div><h1>$title</h1>$whole</div></body></html>
head: <div>$whole</div>
list+: <ol>$whole</ol>
list: <li>$whole</li>
ulist+: <ul>$whole</ul>
ulist: <li>$whole</li>
table+: <table>$whole</table>
table: <tr>$whole</tr>
code+: <pre>$whole</pre>
code: $whole
par: <p>'''
html_template = dict(re.findall('\n([^:]+): (.*?)$', html_template_str, re.M))

def render_as_html(doc_attr, tree):
    head_idx = doc_attr.get('head_idx')
    def make_section_number(head_idx, level):
        return '.'.join(map(str, head_idx[1:level+1]))
    def head_filter(s):
        m = re.match('^([*]+) *(.*)$', s)
        if not m: return s
        level = len(m.group(1))
        head_idx[level] += 1
        for i in range(level+1, 9):
            head_idx[i] = 0
        return '<h%d><span class="section-number">%s</span>%s</h%d>'%(level+1, make_section_number(head_idx, level), m.group(2), level+1)
    def list_filter(s):
        m = re.match(r'^ *([0-9]+)[.] *(.*)', s)
        if not m: return s
        return m.group(2)
    def ulist_filter(s):
        m = re.match(r'^ *([+]) *(.*)', s)
        if not m: return s
        return m.group(2)
    def table_filter(s):
        cells = s.split('|')
        if len(cells) < 3: return s
        return ''.join('<td>%s</td>'%(cell) for cell in cells[1:-1])
    def code_filter(s):
        return re.sub('^ *:', '', s)
    def default_filter(s):
        return s
    if type(tree) != list: return cgi.escape(tree, True)
    template = html_template.get(tree[0], '$whole')
    filter = locals().get('%s_filter'%(tree[0]), default_filter)
    first_child = filter(render_as_html(doc_attr, tree[1]))
    rest_children = [render_as_html(doc_attr, child) for child in tree[2:]]
    return string.Template(template).substitute(whole='\n'.join([first_child] + rest_children), **doc_attr)

def preprocess_doc(s):
    def get_title(s):
        m = re.search('^#\+title:\s*(.+?)$', s, re.M|re.I)
        return m and m.group(1) or "untitled(render by org2html.py)"
    def normalize_blankline(s):
        return re.sub('(?m)^(\s*\n)+', '\n', s)
    def remove_comments(s):
        return re.sub('(?m)^\s*#.*?$', '', s)
    def trim_common_leading_prefix_space(s):
        prefix_len = min(map(len, re.findall('^(\s*)\S', s)))
        return '\n'.join(line[prefix_len:] for line in s.split('\n'))
    def mark_code(s):
        def do_mark_code(m):
            return re.sub('(?m)^', m.group(1) + ':', trim_common_leading_prefix_space(m.group(2)))
        return re.sub('(?msi)^( *)#\+begin_.*?\n(.*?)\n\s*#\+end_.*?$', do_mark_code, s)
    return get_title(s), remove_comments(mark_code(normalize_blankline(s)))

def postprocess_doc(s):
    def handle_link(s):
        def make_anchor(m):
            return '<a href="%s">%s</a>'%(m.group(1), m.group(2) or m.group(1))
        link_rexp = r'\[\[([^]]+)\](?:\[([^]]*)\])?\]'
        return re.sub(link_rexp, make_anchor, s)
    return handle_link(s)

def org2html(s, header=''):
    title, doc = preprocess_doc(s)
    indent_tree = remove_indent(parse_indent(doc))
    grouped_tree = aggregate_group(indent_tree)
    html = render_as_html(dict(title=title, css=css_str, head_idx=[0] * 9, html_header=header), grouped_tree)
    return postprocess_doc(html)

if __name__ == '__main__':
    if sys.stdin.isatty():
        print __doc__
        sys.exit(1)
    print '<!DOCTYPE html>\n' + org2html(sys.stdin.read())
