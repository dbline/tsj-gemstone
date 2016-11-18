from decimal import Decimal, InvalidOperation
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
from urlparse import urlparse

from django.conf import settings
from django.utils.functional import memoize

from .base import CSVBackend, SkipDiamond, KeyValueError
from .. import models
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

def split_measurements(measurements):
    try:
        length, width, depth = [x for x in MEASUREMENT_RE.split(measurements) if x]
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/puregrowndiamonds.csv')
    # We haven't established an FTP upload yet
    #default_filename = ''

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            stock_number,
            cut,
            color,
            clarity,
            carat_weight,
            certifier,
            cut_grade,
            polish,
            symmetry,
            fluorescence,
            unused_rap_price,
            unused_off_rap,
            carat_price,
            cert_num,
            length,
            width,
            depth,
            depth_percent,
            table_percent,
            girdle,
            culet,
            unused_comment,
            origin,
            unused_memo,
            unused_inscription,
            unused_measurements,
        ) = line

        (
            minimum_carat_weight,
            maximum_carat_weight,
            minimum_price,
            maximum_price,
            must_be_certified,
            verify_cert_images
        ) = self.pref_values

        #comment = cached_clean(comment)
        stock_number = clean(stock_number, upper=True)

        try:
            cut = self.cut_aliases[cached_clean_upper(cut)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(str(cached_clean(carat_weight)))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        color = self.color_aliases.get(cached_clean_upper(color))

        certifier = cached_clean_upper(certifier)
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

        clarity = cached_clean_upper(clarity)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean_upper(cut_grade))
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

        girdle = cached_clean_upper(girdle)
        if not girdle or girdle == '-':
            girdle = ''

        culet = cached_clean_upper(culet)
        polish = self.grading_aliases.get(cached_clean_upper(polish))
        symmetry = self.grading_aliases.get(cached_clean_upper(symmetry))

        fluorescence = cached_clean_upper(fluorescence)
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
            fluorescence_color = cached_clean_upper(fluorescence_color)
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    continue
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id

        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

        """
        cert_image = cert_image.replace('.net//', '.net/').replace('\\', '/').strip()
        if not cert_image:
            cert_image = ''
        elif verify_cert_images and cert_image != '' and not url_exists(cert_image):
            cert_image = ''
        """

        #length, width, depth = split_measurements(measurements)

        if origin.strip() == 'LAB-CREATED':
            manmade = 't'
        else:
            manmade = 'f'

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
            if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                price = (price_before_markup * (1 + markup[2]/100))
                break
        if not price:
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
            moneyfmt(Decimal(carat_price), curr='', sep=''),
            moneyfmt(Decimal(price), curr='', sep=''),
            certifier,
            cert_num,
            '', # cert_image,
            '', # cert_image_local,
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
            '', #comment,
            '', #city,
            '', #state,
            '', #country,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
