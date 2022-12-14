from decimal import Decimal, InvalidOperation
import glob
import logging
import json
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
from unicodedata import decimal
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
from urlparse import urlparse

from django.conf import settings
from django.utils.lru_cache import lru_cache
from django.utils.encoding import iri_to_uri
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
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/purestone.csv')
    infile_glob = os.path.join(settings.FTP_ROOT, 'purestone/*.csv')

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
            raise ImportSourceError('No data file, aborting import.')

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
            stock_number, #  Supplier Lot#
            location, # Location
            cut, #  Cut (Shape)
            color, #  Color
            clarity, #  Clarity
            carat_weight, #  Carat
            certifier, #  Grading Lab
            cut_grade, #  Make (Cut Grade)
            polish, #  Polish
            symmetry, #  Symmetry
            fluorescence, #  Fluorescence Intensity
            rap_price, # Rapaport Price
            rap_discount, #  % Off RAP
            ppc, #  Asking Price Per Carat  (could use the ppc from the file)
            carat_price,  # TOTAL COST of this stone  (we are using this passed TOTAL cost)
            cert_num, #  Certificate Number
            length,
            width,
            depth,
            depth_percent, #  Depth
            table_percent, #  Table
            crown_height,
            crown_angle,
            pavilion_angle,
            pavilion_depth,
            girdle_percent,
            girdle,
            culet,
            lw_ratio,
            comments, # Description / Comments
            inscription, # Inscription #
            cert_image,
            image,  # This points to a .jpg file normally
            video, # This points to a video like .mp4
            video_with_data,
            growth_process, #  This is the lab-grown process used to create the diamond
            color_shade #  not sure what this represents (Blue, White seem to be only choices)
            
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

        comments = cached_clean(comments) or ''
        stock_number = clean(stock_number, upper=True)
        
        manmade = 't'  ## All diamonds in the file ARE lab-grown
        if manmade == 'f' and not include_mined:
                raise SkipDiamond("Don't include mined")
        if manmade == 't' and not include_lab_grown:
                raise SkipDiamond("Don't include lab-grown")

        try:
            cut = self.cut_aliases[cached_clean(cut, upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(str(cached_clean(carat_weight)))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)
       
        try:
            color = self.color_aliases[cached_clean(color, upper=True)]
        except KeyError as e:
            raise KeyValueError('color_aliases', e.args[0])

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
            raise SkipDiamond('Certifier {0} disabled'.format(certifier))

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
        
        # length, width, depth = split_measurements(dimensions)  In this case, we are given them separately

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

        """
        girdle = girdle_thin or ''
        if girdle_thin != girdle_thick and girdle_thick:
            if girdle_thin:
                girdle += ' - ' + girdle_thick
            else:
                girdle = girdle_thick
        """
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

        """
        if fluorescence_color:
            fluorescence_color = cached_clean(fluorescence_color, upper=True)
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    continue
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id
        """
        
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
            
        data = {}
        
        if image:
            image = iri_to_uri(image)
            data['photo'] = image

        if video:
            video = iri_to_uri(video)
            data['video'] = video
            
        if inscription:
            data['inscription'] = inscription
            laser_inscribed = 't'
        else:
            laser_inscribed = 'f'
            
        if rap_discount:
            rap_discount = iri_to_uri(rap_discount)
            data['photo'] = rap_discount

        if rap_price:
            rap_price = iri_to_uri(rap_price)
            data['rap_price'] = rap_price
            
        if ppc:
            data['ppc'] = ppc
            
        if lw_ratio:
            data['lw_ratio'] = lw_ratio
            
        if crown_angle:
            data['crown_angle'] = crown_angle
            
        if crown_height:
            data['crown_height'] = crown_height
            
        if pavilion_angle:
            data['pavilion_angle'] = pavilion_angle
            
        if pavilion_depth:
            data['pavilion_depth'] = pavilion_depth
            
        if girdle_percent:
            data['girdle_percent'] = girdle_percent
            
        if video_with_data:
            video_with_data = iri_to_uri(video_with_data)
            data['video_with_data'] = video_with_data
            
        if growth_process:
            data['growth_process'] = growth_process
            
        if color_shade:
            data['color_shade'] = color_shade
            
            
            
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
            cert_image, # cert_image,
            '', # cert_image_local,
            depth_percent,
            table_percent,
            girdle, # girdle,
            culet, # culet,
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
            comments, # comment,
            '', # city
            '', # state,
            location, # country,
            manmade,  # manmade,
            laser_inscribed,  # laser_inscribed,
            'NULL',  # rap_date
            json.dumps(data) # multiuse json blob
        )

        return ret
