from decimal import Decimal, InvalidOperation
import glob
import logging
import json
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
from urlparse import urlparse

from django.conf import settings
from django.utils.lru_cache import lru_cache
from thinkspace.utils.http import url_exists

from .base import LRU_CACHE_MAXSIZE, CSVBackend, SkipDiamond, KeyValueError, ImportSourceError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

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
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/pologem.csv')
    infile_glob = os.path.join(settings.FTP_ROOT, 'pologem-ftp/dia*csv')

    def digits_check(self, s, length=5):
        if sum(c.isdigit() for c in str(s)) > length:
            self.logger.info('Skipping Diamond "%s" - numeric value out of range' % stock_number)
            raise SkipDiamond('numeric value out of allowed range')
        return

    def get_default_filename(self):
        try:
            fn = max(glob.iglob(self.infile_glob), key=os.path.getctime)
        except ValueError:
            fn = None
        if not fn:
            raise ImportSourceError('No Gemex file, aborting import.')

        return fn

    @property
    def enabled(self):
        try:
            return self.backend_module in prefs.get('backend')
        except TypeError:
            return False

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            cut, #  Cut (Shape)
            carat_weight, #  Carat
            color, #  Color
            clarity, #  Clarity
            unused_measurements, 
            cut_grade, #  Make (Cut Grade)
            certifier, #  Grading Lab
            carat_price, #  Asking Price Per Carat
            depth_percent, #  Depth
            table_percent, #  Table
            girdle_thin, #  Girdle From
            girdle_thick, #  Girdle To
            unused_girdle_condition, #not carried
            culet, #  Culet Size
            polish, #  Polish
            symmetry, #  Symmetry
            fluorescence, #  Fluorescence Intensity
            fluorescence_color, #  Fluorescence Color
            unused_crown_height, #  Crown Height
            unused_crown_angle, #  Crown Angle
            unused_pavilion_depth, #  Pavilion Depth
            unused_pavilion_angle, #  Pavilion Angle
            laser_inscribed, # Laser inscription (set to True)
            comment, #  Remarks
            cert_num, #  Certificate Number
            cert_image, #  Certificate File
            unused_diamond_image,  #URI to the image file (.jpg)
            stock_number, #  Supplier Stock Ref
            unused_matching_stock_number, #  Matching Pair Stock Ref
            unused_is_pair_separable, #  Pair is Seperable
            unused_fancy_color_id, #  Natural Fancy Color
            unused_fancy_color_intensity_id, #  Natural Fancy Intensity
            unused_fancy_color_overtone_id, #  Natural Fancy Overtone
            unused_status,
            unused_raplist,
            unused_rap_discount,
            unused_shade, #  Shade
            length, #  Length
            width, #  Width
            depth, #  Height
            unused_city,
            state, #  State / Region
            country, #  Country
            v360_link, #  Image File 
            unused_enhancement, #  Enhancement
            
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

        comment = cached_clean(comment)
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

        """
        if fancy_color:
            color = None
            fancy_color = cached_clean(fancy_color.replace('-', ' ').lower())
            fancy_color_id = self.fancy_colors.get(fancy_color)
        else:
            fancy_color_id = None
            color = self.color_aliases.get(cached_clean(color, upper=True))

        if fancy_color_intensity:
            fancy_color_intensity = cached_clean(fancy_color_intensity.replace('-', ' ').lower())
            fancy_color_intensity_id = self.fancy_color_intensities.get(fancy_color_intensity)
        else:
            fancy_color_intensity_id = None

        if fancy_color_overtone:
            fancy_color_overtone = cached_clean(fancy_color_overtone.replace('-', ' ').lower())
            fancy_color_overtone_id = self.fancy_color_overtones.get(fancy_color_overtone)
        else:
            fancy_color_overtone_id = None
            
        """

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

        cert_num = stock_number
        if not cert_num:
            cert_num = ''

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        # Initialize price after all other data has been initialized
        price_before_markup = carat_price   #this vendor supplys a TOTAL stone price, NOT ppc.
        carat_price = price_before_markup / carat_weight  #work back to a ppc price for the table
        #price_before_markup = carat_price * carat_weight

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
            
        if v360_link:
            data = {'v360_link': v360_link}
        else:
            data = {}

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
            'NULL',  # self.nvl(fancy_color_id),
            'NULL',  # self.nvl(fancy_color_intensity_id),
            'NULL',  # self.nvl(fancy_color_overtone_id),
            self.nvl(self.digits_check(length)),
            self.nvl(self.digits_check(width)),
            self.nvl(self.digits_check(depth)),
            comment,
            '', # city
            state,
            country,
            'f',  # manmade,
            'f',  # laser_inscribed,
            'NULL',  # rap_date
            json.dumps(data), # data
        )

        return ret