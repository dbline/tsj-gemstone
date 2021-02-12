from decimal import Decimal, InvalidOperation
import glob
import logging
import os
import re
import six
from string import ascii_letters, digits, whitespace, punctuation

from django.conf import settings
from django.utils.lru_cache import lru_cache

import requests

from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

from .base import (LRU_CACHE_MAXSIZE, XMLBackend, XMLHandler, ImportSourceError,
                   SkipDiamond, KeyValueError, SkipImport)

logger = logging.getLogger(__name__)

XML_URL = 'http://1800gia.com/xml.php'

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    if data is None:
        return ''
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

class MDLHandler(XMLHandler):
    def __init__(self, backend, writer):
        # ContentHandler is an old-style class
        XMLHandler.__init__(self, backend, writer)

        self.fields = ('shape', 'weight', 'colour', 'clarity', 'make', 'price', 'certtype')
        self.dimension_fields = ('maximum', 'minimum', 'depth')
        self.row = {}
        self.dimensions = {}
        self.char_buffer = []

    def startElement(self, name, attrs):
        name = name.encode('utf-8').strip()
        if name == 'diamond':
            self.row['stock_number'] = attrs.get('id')

        # TODO: Check/convert currency?  Currently all CAD
        #if name == 'price':
        #    ...

    def characters(self, data):
        data = data.encode('utf-8').strip()
        if data:
            self.char_buffer.append(data)

    def endElement(self, name):
        name = name.encode('utf-8').strip()
        if name == 'diamond':
            self.backend.try_write_row(self.writer, self.row)
            self.row = {}
        elif name == 'dimensions':
            self.row.update(self.dimensions)
            self.dimensions = {}
        elif name in self.fields and self.char_buffer:
            self.row[name] = ''.join(self.char_buffer)
        elif name in self.dimension_fields and self.char_buffer:
            self.dimensions[name] = ''.join(self.char_buffer)

        self.char_buffer = []

    def endDocument(self):
        if self.backend.row_buffer:
            self.writer.writerows(self.backend.row_buffer)

class Backend(XMLBackend):
    handler_class = MDLHandler

    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/mdl.xml')

    def get_fp(self):
        fn = ''
        url = ''
        if self.filename:
            fn = self.filename
        elif settings.DEBUG and not self.nodebug:
            fn = self.debug_filename
        else:
            url = XML_URL

        if fn:
            try:
                return open(fn, 'rU')
            except IOError as e:
                raise ImportSourceError(str(e))
        elif url:
            # TODO: Catch HTTP errors
            response = requests.get(url)
            if not response:
                raise SkipImport
            return six.moves.cStringIO(response.content)
        else:
            raise SkipImport

    def write_diamond_row(self, data):
        (
            minimum_carat_weight,
            maximum_carat_weight,
            minimum_price,
            maximum_price,
            must_be_certified,
            verify_cert_images,
            include_mined,
            include_lab_grown
        ) = self.pref_values

        stock_number = clean(data.get('stock_number'))

        try:
            cut = self.cut_aliases[cached_clean(data.get('shape'), upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(str(cached_clean(data.get('weight'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        color = self.color_aliases.get(cached_clean(data.get('colour'), upper=True))
        if not color:
            raise SkipDiamond('No color was specified.')

        certifier = cached_clean(data.get('certtype'), upper=True)
        # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
        if must_be_certified:
            if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
                raise SkipDiamond('No valid certifier was specified.')
        try:
            certifier_id, certifier_disabled = self.certifier_aliases[certifier]
        except KeyError as e:
            #raise KeyValueError('certifier_aliases', e.args[0])
            certifier_id = None
            certifier_disabled = False

        if certifier_disabled:
            raise SkipDiamond('Certifier disabled')

        if certifier and not certifier_id:
            new_certifier = models.Certifier.objects.create(name=certifier, abbr=certifier)
            self.certifier_aliases.update({certifier: (int(new_certifier.id), new_certifier.disabled)})
            certifier = new_certifier.pk
        else:
            certifier = certifier_id

        clarity = cached_clean(data.get('clarity'), upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(data.get('make'), upper=True))

        try:
            price = clean(data.get('price').replace(',', ''))
            if price:
                price = Decimal(price)
            else:
                price = None
        except AttributeError:
            price = None

        length = clean(data.get('maximum'))
        width = clean(data.get('minimum'))
        depth = clean(data.get('depth'))

        if length and float(length) >= 1000.00:
            raise SkipDiamond('Length too large ( >= 1000)')
        if depth and float(depth) >= 1000.00:
            raise SkipDiamond('Depth too large ( >= 1000)')
        if width and float(width) >= 1000.00:
            raise SkipDiamond('Width too large ( >= 1000)')

        cert_num = clean(data.get('certnum'))
        if not cert_num:
            cert_num = ''

        if price is None:
            raise SkipDiamond('No price specified')

        # FIXME: MDL carat price or total price?
        # Initialize price after all other data has been initialized
        # ASC already includes total price
        price_before_markup = price
        carat_price = price / carat_weight

        if minimum_price and price_before_markup < minimum_price:
            raise SkipDiamond('Price before markup is less than the minimum of %s.' % minimum_price)
        if maximum_price and price_before_markup > maximum_price:
            raise SkipDiamond('Price before markup is greater than the maximum of %s.' % maximum_price)

        price = None
        for markup in self.markup_list:
            if prefs.get('markup') == 'carat_weight':
                if markup[0] <= carat_weight and markup[1] >= carat_weight:
                    price = (price_before_markup * (1 + markup[2]/100))
                    break
            else:
                if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                    price = (price_before_markup * (1 + markup[2]/100))
                    break

        if not price:
            if prefs.get('markup') == 'carat_weight':
                raise SkipDiamond("A diamond markup doesn't exist for a diamond with carat weight of %s." % carat_weight)
            else:
                raise SkipDiamond("A diamond markup doesn't exist for a diamond with pre-markup price of %s." % price_before_markup)

        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active,
            self.backend_module,
            '', # lot_num
            stock_number,
            '', # owner
            cut,
            self.nvl(cut_grade),
            self.nvl(color),
            clarity,
            carat_weight,
            moneyfmt(Decimal(price_before_markup), curr='', sep=''),
            moneyfmt(Decimal(carat_price), curr='', sep=''),
            moneyfmt(Decimal(price), curr='', sep=''),
            self.nvl(certifier),
            cert_num,
            '', # cert_image
            '', # cert_image_local
            'NULL', # depth_percent,
            'NULL', # table_percent,
            '', # girdle
            '', # culet
            'NULL', # self.nvl(polish),
            'NULL', # self.nvl(symmetry),
            'NULL', # self.nvl(fluorescence_id),
            'NULL', # self.nvl(fluorescence_color_id)
            'NULL', # self.nvl(fancy_color_id),
            'NULL', # self.nvl(fancy_color_intensity_id),
            'NULL', # self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            '', # comment
            '', # city
            '', # state
            '', # country
            'f', # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
