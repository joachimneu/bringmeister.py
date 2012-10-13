#! /usr/bin/python

import sys
import re
from bringmeister import BringmeisterClient

bc = BringmeisterClient('products_dump.json', raw_input('Your Bringmeister.de email address: '), raw_input('Your Bringmeister.de password: '))

# as the goods that are available in your delivery area
# might differ, you might want to refresh your product
# cache from time to time ...
#bc.product_cache_refresh()

# select the last possible delivery time slot
bc.timeslot_select(bc.timeslot_list()[-1])

# take the first match for the given regexp ...
p = list(bc.search_products_regexp(re.compile("Berchtesgadener Frische Milch 1,5%".lower(), flags=re.I)))[0]
# ... and add 1 piece of it to the shopping cart
bc.cart_add_product(p, 1, BringmeisterClient.AMOUNT_PIECES)

# export the session cookies to Epiphany browser ...
bc.cookies_export_to_epiphany()
# ... and fire off Epiphany to complete checkout
import os
os.system('epiphany-browser https://www.bringmeister.de/Shop/checkout/overview')
