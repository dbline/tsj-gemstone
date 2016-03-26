from decimal import Decimal, InvalidOperation
import glob
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
from urlparse import urlparse

from django.conf import settings
from django.db import connection, transaction
from django.utils.functional import memoize

from .base import CSVBackend, SkipDiamond, KeyValueError
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

def clean_upper(data):
    return clean(data, upper=True)

_clean_cache = {}
_clean_upper_cache = {}

# Values that are expected to recur within an import can have their
# cleaned values cached with these wrappers.  Since memoize can't
# handle kwargs, we have a separate wrapper for using upper=True
cached_clean = memoize(clean, _clean_cache, 2)
cached_clean_upper = memoize(clean_upper, _clean_upper_cache, 2)

# GN combines fluorescence and fluorescence_color
FLUORESCENCE_MAP = {
    #'DIST.': (None, None),
    #'DIST.B': (None, 'B'),
    #'DST': (None, None),
    'F': ('F', None),
    'FB': ('F', 'B'),
    'FNT BL': ('F', 'B'),
    #'LB': (None, 'B'),
    'MB': ('M', 'B'),
    'MODER': ('M', None),
    'MODER.': ('M', None),
    'MODER.-ST': ('M', None),
    'MODER.Y': ('M', 'Y'),
    'MODERATE B.': ('M', 'B'),
    'MY': ('M', 'Y'),
    'N': ('N', None),
    'NON': ('N', None),
    'SB': ('S', 'B'),
    #'SL': (None, None),
    #'SLB': (None, 'B'),
    #'SLT BL': (None, 'B'),
    #'SLY': (None, 'Y'),
    'ST': ('S', None),
    'STB': ('S', 'B'),
    'STG BL': ('S', 'B'),
    'STY': ('S', 'Y'),
    'SY': ('S', 'Y'),
    #'VDIST.B': (None, 'B'),
    'VS': ('VS', None),
    #'VSL': (None, None),
    #'VSL BL': (None, 'B'),
    #'VSLB': (None, 'B'),
    #'VSLY': (None, 'Y'),
    'VSTB': ('VS', 'B'),
    'VSY': ('VS', 'Y'),
}

def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('x')
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(CSVBackend):
    infile_glob = '/glusterfs/ftp_home/gndiamond/upload/Diamond*txt'
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/gndiamond.csv')

    def get_default_filename(self):
        files = sorted(glob.glob(self.infile_glob))
        if len(files):
            fn = files[-1]
            logger.info('Importing GN Diamond file "%s"' % fn)
            return fn

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        # Order must match structure of CSV spreadsheet
        (
            cut,
            carat_weight,
            color,
            clarity,
            cut_grade,
            carat_price,
            off_rap, # TODO: What's this?
            certifier,
            depth_percent,
            table_percent,
            girdle,
            culet,
            polish,
            fluorescence,
            symmetry,
            brand,
            crown,
            pavilion,
            measurements, # LxWxD
            comment,
            num_stones,
            unused_cert_num,
            stock_number,
            pair,
            pair_separable,
            unused_fancy_color,
            trade_show,
            cert_num,
            show_cert, # Yes/No
            fancy, # Just Yellow so far
            sarine_link
        ) = line

        #minimum_carat_weight, maximum_carat_weight, minimum_price, maximum_price, must_be_certified, verify_cert_images = pref_values
        # TODO: Until we have prefs
        minimum_carat_weight = 0
        maximum_carat_weight = None
        minimum_price = 0
        maximum_price = False
        must_be_certified = True

        comment = cached_clean(comment)
        stock_number = clean(stock_number, upper=True)
        owner = 'GN'

        # Brand (Forever After, Hearts & Arrows, Fancy Yellow)
        if fancy:
            brand = 'FANCY'
            # TODO: The FancyColor model isn't in the dev branch yet
            #fancy_color = self.fancy_color_aliases.get(cached_clean_upper(color))
            color = None
        else:
            brand = brand
            color = self.color_aliases.get(cached_clean_upper(color))
            fancy_color = None

        try:
            cut = self.cut_aliases[cached_clean_upper(cut)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(str(cached_clean(carat_weight)))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond("Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight))
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond("Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight))

        certifier = cached_clean_upper(certifier)
        # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
        if must_be_certified:
            if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
                raise SkipDiamond('No valid Certifier was specified.')
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

        clarity = cached_clean_upper(clarity)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean_upper(cut_grade))
        carat_price = clean(carat_price.replace(',', ''))
        if carat_price:
            carat_price = Decimal(carat_price)
        else:
            carat_price = None

        try:
            depth_percent = Decimal(str(clean(depth_percent)))
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(table_percent)))
        except InvalidOperation:
            table_percent = 'NULL'

        girdle = cached_clean_upper(girdle)
        if not girdle or girdle == '-':
            girdle = ''

        culet = cached_clean_upper(culet)
        polish = self.grading_aliases.get(cached_clean_upper(polish))
        symmetry = self.grading_aliases.get(cached_clean_upper(symmetry))

        fluorescence = cached_clean_upper(fluorescence)
        if fluorescence in FLUORESCENCE_MAP:
            f, c = FLUORESCENCE_MAP[fluorescence]
            fluorescence_id = self.fluorescence_aliases[f]
            if c:
                fluorescence_color_id = self.fluorescence_color_aliases[c]
            else:
                fluorescence_color_id = None
        else:
            fluorescence_id = None
            fluorescence_color_id = None

        measurements = clean(measurements)
        length, width, depth = split_measurements(measurements)

        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

        show_cert = clean(show_cert)
        if show_cert == 'Yes':
            cert_image = 'http://gndiamond.s3.amazonaws.com/certificates/%s.jpg' % (stock_number)
        else:
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

        # Order must match struture of tsj_gemstone_diamond table
        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active
            self.backend_module,
            '', # lot_num
            stock_number,
            owner,
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
            '', # state,
            '', # country,
            'NULL', # rap_date
        )

        return ret
