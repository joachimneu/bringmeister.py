#! /usr/bin/python

import sys
import re
from bringmeister import BringmeisterClient

bc = BringmeisterClient('products_dump.json')

for p in bc.search_products_regexp(re.compile(sys.argv[1].lower(), flags=re.I)):
	print p.pnr, p.url, p.name1, p.name2, p.packaging
