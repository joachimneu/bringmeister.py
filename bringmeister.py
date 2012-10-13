#! /usr/bin/python
# -*- encoding: utf8 -*-

import json
import mechanize
from lxml.html import parse

class BringmeisterException(Exception):
	pass

class BringmeisterFormNotFoundException(BringmeisterException):
	pass

class BringmeisterUnknownAmountDescriptionException(BringmeisterException):
	pass

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

class BringmeisterTimeslot:
	def __init__(self, datetime_begin, datetime_end, link, price):
		self.datetime_begin = datetime_begin
		self.datetime_end = datetime_end
		self.link = link
		self.price = price
	
	def __repr__(self):
		return 'BringmeisterTimeslot: ' + repr(self.datetime_begin) + ' to ' + repr(self.datetime_end) + ' (' + repr(self.price) + ')'

def _cmp_bringmeister_timeslots(x, y):
	if x.datetime_begin > y.datetime_begin:
		return 1
	elif x.datetime_begin == y.datetime_begin:
		return 0
	else:
		return -1

class BringmeisterClient:
	AMOUNT_PIECES = 'AMOUNT-PIECES'
	AMOUNT_G = 'AMOUNT-G'
	AMOUNT_KG = 'AMOUNT-KG'
	
	def __init__(self, product_cache_file=None, email=None, password=None):
		self.product_cache_file = product_cache_file
		self.products = {}
		if self.product_cache_file:
			self.product_cache_read()
		self.browser = mechanize.Browser()
		self.browser.set_handle_robots(False)
		self.email = email
		self.password = password
		self.logout()
		if self.email:
			self.login()
	
	def logout(self):
		self.browser.open('https://www.bringmeister.de/Shop/logout')
	
	def login(self):
		self.browser.open('https://www.bringmeister.de/Shop/login')
		for f in self.browser.forms():
			if f.action == 'https://www.bringmeister.de/Shop/login/stamm':
				self.browser.form = f
				self.browser['account'] = self.email
				self.browser['pw'] = self.password
				self.browser.submit()
				return
		raise BringmeisterFormNotFoundException
	
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
				product.amount_options = []
				for o in p.cssselect('td.col_price div.options option'):
					if o.get('value') == 'S':
						product.amount_options.append(self.AMOUNT_PIECES)
					elif o.get('value') == 'G':
						product.amount_options.append(self.AMOUNT_G)
					elif o.get('value') == 'KG':
						product.amount_options.append(self.AMOUNT_KG)
					else:
						print o, o.get('value'), o.text_content()
						raise BringmeisterUnknownAmountDescriptionException
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
	
	def cart_add_product(self, product, amount, amount_type):
		self.browser.open(product.url)
		self.browser.select_form(name='productsubmit')
		self.browser['cnt'] = str(amount)
		if amount_type == self.AMOUNT_PIECES:
			self.browser['vke'] = ['S']
		elif amount_type == self.AMOUNT_G:
			self.browser['vke'] = ['G']
		elif amount_type == self.AMOUNT_KG:
			self.browser['vke'] = ['KG']
		else:
			print amount_type
			raise BringmeisterUnknownAmountDescriptionException
		self.browser.submit()
	
	def timeslot_list(self):
		import datetime
		node_root = parse(self.browser.open('http://www.bringmeister.de/Shop/timeslot')).getroot()
		timeslots = []
		weeks = []
		for w in node_root.cssselect('div.calendar_column div.selectbox div.weekpic > div'):
			weeks.append({})
			weeks[-1]['start'] = datetime.datetime(int(w.text_content().split('-')[0].strip().split('.')[2]), int(w.text_content().split('-')[0].strip().split('.')[1]), int(w.text_content().split('-')[0].strip().split('.')[0]))
		for i in range(len(weeks)):
			j = 0
			for e in node_root.cssselect('div.calendar_column div.date_wrap.w%d > div'% (i,)):
				if not e.get('class') in ['line', 'first', 'clear', None]:
					datetime_start = weeks[i]['start'] + datetime.timedelta(days=j%7)
					if j < 7:
						datetime_start += datetime.timedelta(seconds=3600*9)
					elif j < 14:
						datetime_start += datetime.timedelta(seconds=3600*10)
					elif j < 21:
						datetime_start += datetime.timedelta(seconds=3600*11)
					elif j < 28:
						datetime_start += datetime.timedelta(seconds=3600*12)
					elif j < 35:
						datetime_start += datetime.timedelta(seconds=3600*13)
					elif j < 42:
						datetime_start += datetime.timedelta(seconds=3600*14)
					elif j < 49:
						datetime_start += datetime.timedelta(seconds=3600*15)
					elif j < 56:
						datetime_start += datetime.timedelta(seconds=3600*16)
					elif j < 63:
						datetime_start += datetime.timedelta(seconds=3600*17)
					elif j < 70:
						datetime_start += datetime.timedelta(seconds=3600*18)
					elif j < 77:
						datetime_start += datetime.timedelta(seconds=3600*19)
					else:
						raise BringmeisterException
					datetime_end = datetime_start + datetime.timedelta(seconds=3600*2)
					if e.get('class') == 'timeslot_square':
						link = e.cssselect('a')[0].get('href')
						price = float(''.join([ c for c in e.cssselect('a')[0].text_content().strip() if c in '0123456789' ]))
						timeslots.append(BringmeisterTimeslot(datetime_start, datetime_end, link, price))
					j += 1
		timeslots.sort(_cmp_bringmeister_timeslots)
		return timeslots
	
	def timeslot_select(self, timeslot):
		self.browser.open(timeslot.link)
		self.browser.open('http://www.bringmeister.de/Shop/timeslot/save')
	
	def cookies_export_to_epiphany(self):
		for c in self.browser._ua_handlers['_cookies'].cookiejar:
			print c
			c_name = c.name
			c_value = c.value
			c_expires = c.expires
			if c_name == 'askzipcode':
				c_value = '0'
			self._cookies_export_to_epiphany(c_name, c_value, c_expires)

	def _cookies_export_to_epiphany(self, c_name, c_value, c_expires):
		import os
		import sqlite3
		conn = sqlite3.connect(os.environ['HOME'] + '/.gnome2/epiphany/cookies.sqlite')
		c = conn.cursor()
		c.execute('DELETE FROM moz_cookies WHERE name=\'%s\' AND host=\'www.bringmeister.de\''% (c_name,))
		c.execute('INSERT INTO moz_cookies(name, value, host, path, expiry, lastAccessed, isSecure, isHttpOnly) VALUES(\'%s\', \'%s\', \'www.bringmeister.de\', \'/\', \'%d\', \'\', 0, 0)'% (c_name, c_value, c_expires))
		conn.commit()
		conn.close()
