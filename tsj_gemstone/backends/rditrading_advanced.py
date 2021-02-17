from decimal import Decimal, InvalidOperation
import glob
import json
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
from urlparse import urlparse

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import LRU_CACHE_MAXSIZE, CSVBackend, SkipDiamond, KeyValueError, ImportSourceError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt
from thinkspace.utils.http import url_exists

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))
# TODO: Need to handle spaces between dimensions
MEASUREMENT_RE = re.compile('[\sx*-]')

def clean(data, upper=False):
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

def split_measurements(measurements):
    try:
        length, width, depth = [x for x in MEASUREMENT_RE.split(measurements) if x]
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/rditrading_advanced.csv')
    infile_glob = os.path.join(settings.FTP_ROOT, 'rdi-global-diamond-feed/*csv')

    def get_default_filename(self):
        try:
            fn = max(glob.iglob(self.infile_glob), key=os.path.getctime)
        except ValueError:
            fn = None
        if not fn:
            raise ImportSourceError('No rdi-trading file, aborting import.')

        return fn

    """
    "Shape",
    "Weight",
    "Color",
    "Clarity",
    "Measurements",
    "Cut Grade",
    "Lab",
    "Price",
    "Depth %",
    "Table %",
    "Girdle Min",
    "Girdle Max",
    "Girdle Condition",
    "Culet Size",
    "Polish",
    "Symmetry",
    "Fluorescence Intensity",
    "Fluorescence Color",
    "Crown Height",
    "Crown Angle",
    "Pavilion Depth",
    "Pavilion Angle",
    "Laser Inscription",
    "Comments",
    "Certificate #",
    "Certificate Image",
    "Diamond Image",
    "Vendor Stock Number",
    "Pair Vendor Stock Number",
    "Is Matched Pair Separable",
    "Fancy Color",
    "Fancy Color Intensity",
    "Fancy Color Overtone",
    "Status",
    "RapList",
    "Rap%",
    "Shade",
    "MeasLength",
    "MeasWidth",
    "MeasDepth",
    "City",
    "State",
    "Country",
    "VideoUrl"
    """

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            cut,
            carat_weight,
            color,
            clarity,
            unused_measurements,
            cut_grade,
            certifier,
            carat_price,
            depth_percent,
            table_percent,
            girdle_thin,
            girdle_thick,
            unused_girdle_condition,
            culet,
            polish,
            symmetry,
            fluorescence,
            fluorescence_color,
            unused_crown_height,
            unused_crown_angle,
            unused_pavilion_depth,
            unused_pavilion_angle,
            unused_laser_inscription,
            comment,
            cert_num,
            cert_image,
            image,
            stock_number,
            unused_matching_stock_number,
            unused_is_matched_pair_separable,
            unused_fancy_color,
            unused_fancy_color_intensity,
            unused_fancy_color_overtone,
            unused_status,
            unused_rap_list,
            unused_rap_percent,
            unused_shade,
            length,
            width,
            depth,
            city,
            state,
            country,
            video_url,
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

        girdle = girdle_thin or ''
        if girdle_thin != girdle_thick and girdle_thick:
            if girdle_thin:
                girdle += ' - ' + girdle_thick
            else:
                girdle = girdle_thick

        girdle = cached_clean(girdle, upper=True)
        if not girdle or girdle == '-':
            girdle = ''

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

        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

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

        data = {}
        if video_url:
            data.update({'video_url': video_url})

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
            '', # cert_image_local,
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
            city,
            state,
            country,
            'f', # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            json.dumps(data), # data
        )

        return ret
