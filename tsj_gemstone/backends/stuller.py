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
from django.utils.functional import memoize

from .base import JSONBackend, SkipDiamond, KeyValueError
from .. import models
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    if data is None:
        return ''
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

def clean_upper(data):
    return clean(data, upper=True)

_clean_cache = {}
_clean_upper_cache = {}

# Values that are expected to recur within an import can have their
# cleaned values cached with these wrappers.  Since memoize can't
# handle kwargs, we have a separate wrapper for using upper=True
cached_clean = memoize(clean, _clean_cache, 2)
cached_clean_upper = memoize(clean_upper, _clean_upper_cache, 2)

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
        url = 'https://www.stuller.com/api/v2/gem/diamonds'

        next_page = None
        prev_page_hash = None
        serial_numbers = set()
        ret = []

        # Accumulate paginated diamond data into ret
        while True:
            new_serial_numbers = 0

            if next_page:
                # Stuller wants a JSON request body, not urlencoded form data
                response = session.post(url, json={'NextPage': next_page})
            else:
                response = session.get(url)

            if response.status_code != 200:
                logger.error('Stuller HTTP error {}'.format(response.status_code))
                return

            data = response.json()
            if 'Diamonds' not in data:
                break

            for x, d in enumerate(data['Diamonds']):
                if d['SerialNumber'] not in serial_numbers:
                    serial_numbers.add(d['SerialNumber'])
                    new_serial_numbers += 1
                    ret.append(d)

            # If there aren't any new serial numbers, we're probably in an infinite loop
            if not new_serial_numbers:
                logger.warning('Stuller infinite loop (diamond count {})'.format(len(serial_numbers)))
                break

            if 'NextPage' in data and data['NextPage']:
                next_page = data['NextPage']

                # Sometimes we see the same NextPage
                _hash = hashlib.md5(next_page).hexdigest()
                if _hash == prev_page_hash:
                    logger.warning('Stuller infinite loop (hash {})'.format(_hash))
                    break
                prev_page_hash = _hash
                time.sleep(2)
            else:
                break

        return ret

    def write_diamond_row(self, data):
        minimum_carat_weight, maximum_carat_weight, minimum_price, maximum_price, must_be_certified, verify_cert_images = self.pref_values

        stock_number = clean(str(data.get('SerialNumber')))
        comment = cached_clean(data.get('Comments'))
        try:
            cut = self.cut_aliases[cached_clean_upper(data.get('Shape'))]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(cached_clean(str(data.get('CaratWeight'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond("Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight))
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond("Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight))

        color = self.color_aliases.get(cached_clean_upper(data.get('Color')))

        certifier = cached_clean_upper(data.get('Certification'))
        # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
        if must_be_certified:
            if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
                raise SkipDiamond('No valid Certifier was specified.')
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

        clarity = cached_clean_upper(data.get('Clarity'))
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean_upper(data.get('Make')))
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
            girdle_thinnest = cached_clean_upper(data['Girdle'])
            girdle = [girdle_thinnest]
            if data.get('Girdle2'):
                girdle_thickest = cached_clean_upper(data['Girdle2'])
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''

        culet = cached_clean_upper(data.get('Culet'))
        polish = self.grading_aliases.get(cached_clean_upper(data.get('Polish')))
        symmetry = self.grading_aliases.get(cached_clean_upper(data.get('Symmetry')))

        # Fluorescence and color are combined, e.g 'FAINT BLUE'
        fl = data.get('Fluorescence', '')
        if ' ' in fl:
            fl, flcolor = fl.split(' ')
            fluorescence = cached_clean_upper(fl)
            fluorescence_color = cached_clean_upper(flcolor)

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
            raise SkipDiamond("Price before markup '%s' is less than the minimum of %s." % (price_before_markup, minimum_price))
        if maximum_price and price_before_markup > maximum_price:
            raise SkipDiamond("Price before markup '%s' is greater than the maximum of %s." % (price_before_markup, maximum_price))

        price = None
        for markup in self.markup_list:
            if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                price = (price_before_markup * (1 + markup[2]/100))
                break
        if not price:
            raise SkipDiamond("A diamond markup doesn't exist for a diamond with pre-markup price of '%s'." % price_before_markup)

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
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            comment,
            '', # city,
            state,
            country,
            'NULL' # rap_date
        )

        return ret
