import csv
from decimal import Decimal, InvalidOperation
import json
import logging
import os
import random
import re
from string import ascii_letters, digits, whitespace, punctuation
import tempfile
import time

import requests

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import (LRU_CACHE_MAXSIZE, BaseBackend, ImportSourceError,
                   KeyValueError, SkipDiamond)
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

API_URL = 'http://apiservices.vdbapp.com/v2/diamonds'

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    if data is None:
        return ''
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)


class Backend(BaseBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/vdb.json')

    @property
    def enabled(self):
        api_key = prefs.get('vdb_api_key')
        access_token = prefs.get('vdb_access_token')
        return api_key and access_token

    def get_data(self):
        doc = None
        data = []

        if self.filename:
            doc = json.load(open(self.filename, 'rb'))

        # TODO: We should put a couple paginated JSON files in ../tests/data
        #       so that we can run through the loop below when debugging
        if settings.DEBUG and not self.nodebug:
            doc = json.load(open(self.debug_filename, 'rb'))

        if doc:
            for d in doc['response']['body']['diamonds']:
                data.append(d)
            return data

        params = {
            'type': 'Diamond',
            'page_size': 10,
            'page_number': 1,
            'total_or_price_per_carat': 'total_sales_price',
        }

        search_prefs = {
            'price_total_from': prefs.get('rapaport_minimum_price'),
            'price_total_to': prefs.get('rapaport_maximum_price'),
            'size_from': prefs.get('rapaport_minimum_carat_weight'),
            'size_to': prefs.get('rapaport_maximum_carat_weight'),
        }
        for k, v in search_prefs.items():
            if v:
                params[k] = v

        headers = {
            'Authorization': 'Token token={}, api_key={}'.format(prefs.get('vdb_access_token'), prefs.get('vdb_api_key')),
        }

        ids = set()

        # Preliminary request to check that we've got access
        response = requests.get(API_URL, params=params, headers=headers)
        doc = response.json()
        if doc['response']['header']['status'] != 200:
            raise ImportSourceError('VDB Error: %s' % doc['response']['body'])

        # Accumulate paginated diamond data into ret
        while True:
            new_ids = 0
            page_data = []

            response = requests.get(API_URL, params=params, headers=headers)

            doc = response.json()
            for d in doc['response']['body']['diamonds']:
                page_data.append(d)

            if not page_data:
                break

            for row in page_data:
                if row['id'] not in ids:
                    ids.add(row['id'])
                    new_ids += 1
                    data.append(row)

            # If there aren't any new serial numbers, we're probably in an infinite loop
            if not new_ids:
                logger.warning('VDB infinite loop (diamond count {})'.format(len(ids)))
                break

            params['page_number'] = int(params['page_number']) + 1

            # Spread requests out a bit to avoid rate limiting
            time.sleep(random.random()*2.5)

        return data

    def _run(self):
        data = self.get_data()

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        for row in data:
            self.try_write_row(writer, row)

        if self.row_buffer:
            writer.writerows(self.row_buffer)

        return tmp_file

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

        stock_number = clean(str(data.get('stock_num')), upper=True)

        try:
            cut = self.cut_aliases[cached_clean(data.get('shape'), upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(data.get('cut'), upper=True))
        color = self.color_aliases.get(cached_clean(data.get('color'), upper=True))

        clarity = cached_clean(data.get('clarity'), upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        carat_weight = Decimal(cached_clean(str(data.get('size'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        carat_price = Decimal(data['price_per_carat'])
        price_before_markup = Decimal(data['total_sales_price'])

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

        certifier = cached_clean(data.get('lab'), upper=True)
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

        cert_num = clean(data.get('cert_num'))
        if not cert_num:
            cert_num = ''

        cert_image = data.get('cert_url')

        try:
            depth_percent = Decimal(clean(str(data.get('depth_percent'))))
            if depth_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(cached_clean(str(data.get('table_percent'))))
            if table_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            table_percent = 'NULL'

        if data.get('girdle_min'):
            girdle_thinnest = cached_clean(data['girdle_min'])
            girdle = [girdle_thinnest]
            if data.get('girdle_max'):
                girdle_thickest = cached_clean(data['girdle_max'])
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''

        culet = cached_clean(data.get('culet_size'))
        polish = self.grading_aliases.get(cached_clean(data.get('polish'), upper=True))
        symmetry = self.grading_aliases.get(cached_clean(data.get('symmetry'), upper=True))

        fluorescence_id = None
        fluorescence_color_id = None
        fl = data.get('fluor_intensity_long', '')
        if fl:
            fluorescence = cached_clean(fl, upper=True)
            for abbr, id in self.fluorescence_aliases.iteritems():
                if fluorescence.startswith(abbr.upper()):
                    fluorescence_id = id
                    continue

        length = data.get('meas_length')
        width = data.get('meas_width')
        depth = data.get('meas_depth')

        if data.get('laser_inscription'):
            laser_inscribed = 't'
        else:
            laser_inscribed = 'f'

        city = data.get('city')
        state = data.get('state')
        country = data.get('country')

        # We've only seen null owner info
        #owner = data.get('owner_info')

        lot_num = data.get('id')

        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active
            self.backend_module,
            lot_num,
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
            '', # comment,
            self.nvl(city),
            self.nvl(state),
            self.nvl(country),
            'f', # manmade,
            laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
