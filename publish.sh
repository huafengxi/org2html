#!/bin/bash

real_file=`realpath $0`
bin_dir=`dirname $real_file`
if [ -z "$1" ]; then
    echo "please given dest dir!";
    exit 1
fi

dest=$1
for p in `find $dest -name '*.org'`; do
    html=${p%.org}.html
    echo "generate $html"
    cat $p | $bin_dir/org2html.py > $html
    $bin_dir/anchor-right.py $html
done
