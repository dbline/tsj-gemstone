from decimal import Decimal, InvalidOperation
import json
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import tempfile

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import LRU_CACHE_MAXSIZE, CSVBackend, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/waldman.csv')
    default_filename = os.path.join('/srv/volumes/dekum/wdccanada_temp/diamonds/waldman_full.csv')

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            unused_id,
            unused_created,
            unused_created,
            active,
            unused_source,
            unused_lot_num,
            stock_number,
            unused_owner,
            unused_brand,
            unused_image,
            unused_image_local,
            unused_video,
            unused_embed,
            cut,
            cut_grade,
            color,
            clarity,
            carat_weight,
            carat_price,
            cost,
            price,
            unused_off_rap,
            certifier,
            cert_num,
            cert_image,
            unused_cert_image_local,
            depth_percent,
            table_percent,
            girdle,
            culet,
            polish,
            symmetry,
            fluorescence,
            fluorescence_color,
            fancy_color,
            fancy_color_intensity,
            fancy_color_overtone,
            length,
            width,
            depth,
            unused_comment,
            city,
            state,
            country,
            manmade,
            laser_inscribed,
            origin,
            unused_expedited_shipping,
            unused_rap_date,
            unused_data
        ) = line

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

        stock_number = clean(stock_number, upper=True)

        try:
            cut = self.cut_aliases[cached_clean(cut, upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(str(cached_clean(carat_weight)))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        color = self.color_aliases.get(cached_clean(color, upper=True))

        certifier = cached_clean(certifier, upper=True)
        # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
        if must_be_certified:
            if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
                raise SkipDiamond('No valid certifier was specified.')
        try:
            certifier_id, certifier_disabled = self.certifier_aliases[certifier]
        except KeyError as e:
            raise KeyValueError('certifier_aliases', e.args[0])

        if certifier_disabled:
            raise SkipDiamond('Certifier disabled')

        if certifier and not certifier_id:
            new_certifier = models.Certifier.objects.create(name=certifier, abbr=certifier)
            self.certifier_aliases.update({certifier: (int(new_certifier.id), new_certifier.disabled)})
            certifier = new_certifier.pk
        else:
            certifier = certifier_id

        clarity = cached_clean(clarity, upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(cut_grade, upper=True))
        carat_price = clean(carat_price.replace(',', ''))
        try:
            carat_price = Decimal(carat_price)
        except InvalidOperation:
            carat_price = None

        try:
            depth_percent = Decimal(str(clean(depth_percent)))
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(table_percent)))
        except InvalidOperation:
            table_percent = 'NULL'

        culet = cached_clean(culet, upper=True)
        polish = self.grading_aliases.get(cached_clean(polish, upper=True))
        symmetry = self.grading_aliases.get(cached_clean(symmetry, upper=True))

        fluorescence = cached_clean(fluorescence, upper=True)
        fluorescence_id = None
        fluorescence_color = None
        fluorescence_color_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                fluorescence_color = fluorescence.replace(abbr.upper(), '')
                continue
        fluorescence = fluorescence_id

        if fluorescence_color:
            fluorescence_color = cached_clean(fluorescence_color, upper=True)
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    continue
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        # Initialize price after all other data has been initialized
        price_before_markup = carat_price * carat_weight
        markup = Decimal(0.17) # Full Markup
        waldman_markup = price_before_markup * markup
        price_before_markup = price_before_markup + waldman_markup

        if minimum_price and price_before_markup < minimum_price:
            raise SkipDiamond('Price before markup is less than the minimum of %s.' % minimum_price)
        if maximum_price and price_before_markup > maximum_price:
            raise SkipDiamond('Price before markup is greater than the maximum of %s.' % maximum_price)

        price = None
        if manmade == 'f' or not self.lab_markup_list:
            for markup in self.markup_list:
                if prefs.get('markup') == 'carat_weight':
                    if markup[0] <= carat_weight and markup[1] >= carat_weight:
                        price = (price_before_markup * (1 + markup[2]/100))
                        break
                else:
                    if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                        price = (price_before_markup * (1 + markup[2]/100))
                        break
        else:
            for markup in self.lab_markup_list:
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

        # Order must match struture of tsj_gemstone_diamond table
        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active
            self.backend_module,
            '', # lot_num
            stock_number,
            '', # owner,
            cut,
            self.nvl(cut_grade),
            self.nvl(color),
            clarity,
            carat_weight,
            moneyfmt(Decimal(price_before_markup), curr='', sep=''),
            moneyfmt(Decimal(carat_price), curr='', sep=''),
            moneyfmt(Decimal(price), curr='', sep=''),
            certifier,
            cert_num,
            cert_image,
            '', #cert_image_local,
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
            '', #comment,
            '', #city,
            '', #state,
            '', #country,
            manmade,
            laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret

    @property
    def enabled(self):
        try:
            return self.backend_module in prefs.get('backend')
        except TypeError:
            return False
