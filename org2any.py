#!/bin/env python2
# -*- coding: utf-8 -*-
'''
Usage:
cat a.org | ./org2any.py tree
'''
import sys
import re
import itertools
import pprint

indent_spec_str = '''
title,	0,	1024,	^#[+]title:
opt,	0,	1024,	^#[+]
comment,	0,	1024,	^#
head,	-128,	-128,	^([*]+)
list,	0,	+1,	[0-9]+[.]
ulist,	0,	+1,	[+]
table,	0,	1024,	[|].*[|]$
code,	0,	1024,	:
text,	0,	1024,	
'''
indent_spec = [(name, int(indent_as_child), int(indent_as_parent), rexp) for name, indent_as_child, indent_as_parent, rexp in re.findall('\n([^,]+),\t([^,]+),\t([^,]+),\t(.*?)$', indent_spec_str, re.M)]

def parse_tree(doc):
    def get_indent(line):
        for name, indent_as_child, indent_as_parent, rexp, in indent_spec:
            m = re.match("^( *)" + rexp, line, re.I)
            if not m: continue
            text_indent = len(m.group(1)) + (len(m.groups()) > 1 and len(m.group(2)) or 0)
            return name, indent_as_child + text_indent, indent_as_parent + text_indent
        raise Exception("not matched by any spec: %s"%(line))

    def parse_indent(s):
        root = [-65536, 'root']
        stack = [root]
        for line in s.split('\n'):
            name, indent_as_child, indent_as_parent = get_indent(line)
            while indent_as_child <= stack[-1][0]:
                stack.pop()
            new_top = [indent_as_parent, name]
            stack[-1].append(new_top)
            stack.append(new_top)
            stack[-1].append(line)
        return root

    def remove_indent(tree):
        if type(tree) != list: return tree
        return [remove_indent(item) for item in tree[1:]]

    def list_merge(li):
        return reduce(lambda x,y: x+y, li)

    def aggregate_group(tree):
        if type(tree) != list: return tree
        return [tree[0]] + list_merge(gkey == "leaf" and list(group) or [[gkey + '+'] + [aggregate_group(item) for item in group]] for gkey, group in itertools.groupby(tree[1:], lambda x: type(x) == list and x[0] or 'leaf'))

    indent_tree = remove_indent(parse_indent(doc))
    return aggregate_group(indent_tree)

def get_title(s):
    m = re.search('^#\+title:\s*(.+?)$', s, re.M|re.I)
    return m and m.group(1) or "untitled(render by org2html.py)"

def preprocess_doc(s):
    def normalize_blankline(s):
        return re.sub('(?m)^(\s*\n)+', '\n', s)
    def trim_common_leading_prefix_space(s):
        prefix_len = min(map(len, re.findall('^(\s*)\S', s)))
        return '\n'.join(line[prefix_len:] for line in s.split('\n'))
    def mark_code(s):
        def do_mark_code(m):
            return re.sub('(?m)^', m.group(1) + ':', trim_common_leading_prefix_space(m.group(2)))
        return re.sub('(?msi)^( *)#\+begin_.*?\n(.*?)\n\s*#\+end_.*?$', do_mark_code, s)
    return mark_code(normalize_blankline(s))

def parse_org(s):
    doc = preprocess_doc(s)
    return get_title(doc), parse_tree(doc)
    
if __name__ == '__main__':
    pprint.pprint(parse_org(sys.stdin.read()))
