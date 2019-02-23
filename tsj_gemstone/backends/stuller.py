from decimal import Decimal, InvalidOperation
import hashlib
import json
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import time

import requests

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import LRU_CACHE_MAXSIZE, JSONBackend, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt
from thinkspace.utils.http import url_exists

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    if data is None:
        return ''
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('x')
        if float(length) > 100 or float(width) > 100 or float(depth) > 100:
            raise ValueError
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(JSONBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/stuller.json')

    def get_json(self):
        if self.filename:
            return json.load(open(self.filename, 'rb'))['Diamonds']

        # TODO: We should put a couple paginated JSON files in ../tests/data
        #       so that we can run through the loop below when debugging
        if settings.DEBUG and not self.nodebug:
            return json.load(open(self.debug_filename, 'rb'))['Diamonds']

        session = requests.Session()
        session.auth = (settings.STULLER_USER, settings.STULLER_PASSWORD)
        session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})
        url = 'https://www.stuller.com/api/v2/gem'

        next_page = None
        prev_page_hash = None
        serial_numbers = set()
        ret = []

        new_serial_numbers = 0

        response = session.get(url)

        if response.status_code != 200:
            logger.error('Stuller HTTP error {}'.format(response.status_code))
            return

        data = response.json()
        if 'Diamonds' not in data:
            logger.warning('Stuller no Diamonds provided')

        for x, d in enumerate(data['Diamonds']):
            if d['SerialNumber'] not in serial_numbers:
                serial_numbers.add(d['SerialNumber'])
                new_serial_numbers += 1
                ret.append(d)

        # If there aren't any new serial numbers, we're probably in an infinite loop
        if not new_serial_numbers:
            logger.warning('Stuller no Diamonds provided')

        return ret

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

        if not data.get('IsDiamond'):
            raise SkipDiamond('Is not a diamond.')

        stock_number = clean(str(data.get('SerialNumber')))
        comment = cached_clean(data.get('Comments'))
        try:
            cut = self.cut_aliases[cached_clean(data.get('Shape'), upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(cached_clean(str(data.get('CaratWeight'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        color = self.color_aliases.get(cached_clean(data.get('Color'), upper=True))

        if not color:
            raise SkipDiamond('Not a standard color.')

        certifier = cached_clean(data.get('Certification'), upper=True)
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

        clarity = cached_clean(data.get('Clarity'), upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(data.get('Make'), upper=True))
        try:
            if isinstance(data.get('PricePerCarat'), dict):
                # TODO: Verify that data['PricePerCarat']['CurrencyCode'] is USD
                carat_price = clean(str(data['PricePerCarat'].get('Value')))
                if carat_price:
                    carat_price = Decimal(carat_price)
                else:
                    carat_price = None
            else:
                carat_price = None
        except AttributeError:
            raise
            carat_price = None

        try:
            depth_percent = Decimal(clean(str(data.get('Depth'))))
            if depth_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(cached_clean(str(data.get('Table'))))
            if table_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            table_percent = 'NULL'

        if data.get('Girdle'):
            girdle_thinnest = cached_clean(data['Girdle'], upper=True)
            girdle = [girdle_thinnest]
            if data.get('Girdle2'):
                girdle_thickest = cached_clean(data['Girdle2'], upper=True)
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''

        culet = cached_clean(data.get('Culet'), upper=True)
        polish = self.grading_aliases.get(cached_clean(data.get('Polish'), upper=True))
        symmetry = self.grading_aliases.get(cached_clean(data.get('Symmetry'), upper=True))

        # Fluorescence and color are combined, e.g 'FAINT BLUE'
        fl = data.get('Fluorescence', '')
        if ' ' in fl:
            fl, flcolor = fl.split(' ')
            fluorescence = cached_clean(fl, upper=True)
            fluorescence_color = cached_clean(flcolor, upper=True)

            for abbr, id in self.fluorescence_aliases.iteritems():
                if fluorescence.startswith(abbr.upper()):
                    fluorescence_id = id
                    continue
            fluorescence = fluorescence_id

            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    continue
            if fluorescence_color_id:
                fluorescence_color = fluorescence_color_id
            else:
                fluorescence_color_id = None
        else:
            fluorescence_id = None
            fluorescence_color_id = None

        measurements = clean(data.get('Measurements'))
        length, width, depth = split_measurements(measurements)

        cert_num = clean(data.get('CertificationNumber'))
        if not cert_num:
            cert_num = ''

        cert_image = data.get('CertificatePath')
        if not cert_image:
            cert_image = ''
        elif verify_cert_images and cert_image != '' and not url_exists(cert_image):
            cert_image = ''

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        # Initialize price after all other data has been initialized
        price_before_markup = carat_price * carat_weight

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

        state = cached_clean(data.get('st'))
        country = cached_clean(data.get('cty'))

        # TODO: Matching pair stock number is data['psr']

        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active
            self.backend_module,
            '', # lot_num
            stock_number,
            '', # owner
            cut,
            self.nvl(cut_grade),
            self.nvl(color),
            clarity,
            carat_weight,
            moneyfmt(Decimal(carat_price), curr='', sep=''),
            moneyfmt(Decimal(price), curr='', sep=''),
            certifier,
            cert_num,
            cert_image,
            '', # cert_image_local
            depth_percent,
            table_percent,
            girdle,
            culet,
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence_id),
            self.nvl(fluorescence_color_id),
            'NULL', # self.nvl(fancy_color_id),
            'NULL', # self.nvl(fancy_color_intensity_id),
            'NULL', # self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            comment,
            '', # city,
            state,
            country,
            'f', # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
