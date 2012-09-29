#! /usr/bin/python
# -*- encoding: utf8 -*-

import json
import mechanize
from lxml.html import parse

class FIFO:
	def __init__(self):
		self.data = []
	
	def put(self, obj):
		self.data.insert(0, obj)
	
	def get(self):
		return self.data.pop()
	
	def is_empty(self):
		if len(self.data) == 0:
			return True
		return False
	
	empty = property(is_empty)

class BringmeisterProduct:
	def __init__(self):
		pass

class BringmeisterProductEncoder(json.JSONEncoder):
	def default(self, obj):
		if not isinstance(obj, BringmeisterProduct):
			return super(BringmeisterProductEncoder, self).default(obj)
		
		obj.__dict__['__bringmeister_product__'] = True
		return obj.__dict__

def bringmeister_product_decode(obj):
	if '__bringmeister_product__' in obj:
		p = BringmeisterProduct()
		for k, v in obj.items():
			setattr(p, k, v)
		return p
		
	return obj

class BringmeisterClient:
	def __init__(self, product_cache_file=None):
		self.product_cache_file = product_cache_file
		self.products = {}
		if self.product_cache_file:
			self.product_cache_read()
		self.browser = mechanize.Browser()
		self.browser.set_handle_robots(False)
	
	def product_cache_refresh(self):
		links = FIFO()
		links.put('https://www.bringmeister.de/Shop/maingroup/1')
		links.put('https://www.bringmeister.de/Shop/maingroup/2')
		links.put('https://www.bringmeister.de/Shop/maingroup/3')

		visited = []

		products = {}

		browser = self.browser
		browser.open('https://www.bringmeister.de/Shop/')
		browser.open('https://www.bringmeister.de/Shop/sortiment/1/2/listlist')
		browser.open('https://www.bringmeister.de/Shop/sortiment/1/2/listpppall')

		while not links.empty:
			url = links.get()
			print url,
			if url in visited:
				print 'skipped!'
				continue
			else:
				print '...'
	
			node_root = parse(browser.open(url)).getroot()
			node_nav = node_root.cssselect('div.container div.middle_content div.left_column')[0]
			for href in [ i.get('href') for i in node_nav.cssselect('ul a') ]:
				links.put(href)
	
			for p in node_root.cssselect('div.container div.middle_content div.middle_column div.product_listb table.product'):
				product_url = p.cssselect('td.col_desc a')[0].get('href')
				print '\t', product_url,
				if product_url in products.keys():
					print 'skipped!'
					continue
				else:
					print '...'
		
				product = BringmeisterProduct()
				product.url = product_url
				product.pnr = p.cssselect('td.col_desc p.pnr')[0].text_content().strip()
				product.name1 = p.cssselect('td.col_desc p strong')[0].text_content().strip()
				product.packaging = p.cssselect('td.col_desc p.gray')[0].text_content().strip()
				product.name2 = p.cssselect('td.col_desc span.col_desc')[0].text_content().strip()
				if product.name1:
					product.name2 = product.name2.split(product.name1, 1)[1].strip()
				if product.packaging:
					product.name2 = product.name2.rsplit(product.packaging, 1)[0].strip()
				product.img_small = 'https://www.bringmeister.de' + p.cssselect('td.col_img img')[0].get('src')
				product.price = int(p.cssselect('td.col_price div.pricebar span.price')[0].text_content().strip()[2:]) * 1.0 / 100.0
				product.price_extra = p.cssselect('td.col_price div.pricebar small.extra')[0].text_content().strip()
				if product.price_extra == 'Grundpreis':
					product.price_extra = ''
				elif product.price_extra.startswith(u'Grundpreis€  '):
					product.price_extra = u'Grundpreis: € ' + product.price_extra[13:]
				products[product_url] = product
	
			visited.append(url)

		self.products = products
		self.product_cache_write()

	def product_cache_write(self):
		open(self.product_cache_file, 'w').write(json.dumps(self.products, cls=BringmeisterProductEncoder, sort_keys=True, indent=4))
		
	def product_cache_read(self):
		self.products = json.loads(open(self.product_cache_file, 'r').read(), object_hook=bringmeister_product_decode)
	
	def search_products_regexp(self, regexp):
		for i, obj in self.products.items():
			if regexp.findall(' '.join([obj.pnr, obj.name1, obj.name2, obj.packaging])):
				yield obj
