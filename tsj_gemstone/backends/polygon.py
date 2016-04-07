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
from django.utils.functional import memoize

from .base import CSVBackend, ImportSourceError, SkipDiamond, KeyValueError
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

def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('|')
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(CSVBackend):
    infile_glob = '/glusterfs/ftp_home/polygonftp/{id}*.csv'
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/polygon.csv')

    @property
    def enabled(self):
        return prefs.get('polygon_id')

    def get_default_filename(self):
        polygon_id = prefs.get('polygon_id')

        if not polygon_id:
            # TODO: We shouldn't be able to get here anymore, enabled checks the pref
            logger.warning('Missing Polygon ID, aborting import.')
            return

        files = sorted(glob.glob(self.infile_glob.format(id=polygon_id)))
        if len(files):
            fn = files[-1]
        else:
            raise ImportSourceError('No Polygon file for ID {}, aborting import.'.format(polygon_id))

        return fn

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            owner,
            cut,
            carat_weight,
            color,
            clarity,
            price_before_markup,
            lot_num, # But not really, appears to be a different carat_weight
            stock_number,
            certifier,
            cert_num,
            cert_image,
            unused_second_image,
            measurements,
            depth_percent,
            table_percent,
            crown_angle,
            crown_percent,
            pavilion_angle,
            pavilion_percent,
            girdle_thinnest,
            girdle_thickest,
            girdle_percent, # Ignored for now
            culet_size,
            culet_condition,
            polish,
            symmetry,
            fluorescence_color,
            fluorescence,
            enhancements, # Ignored
            comment,
            availability, # Guaranteed Available, Not Specified, On Memo
            active, # Y/N
            fc_main_body, # Ignored
            fc_intensity, # Ignored
            fc_overtone, # Ignored
            pair, # True/False
            pair_separable, # True/False
            pair_stock_number,
            pavilion,
            syndication,
            cut_grade,
            external_url # Ignored
        ) = line

        if active != 'Y':
            raise SkipDiamond('Diamond is not active')

        (
            minimum_carat_weight,
            maximum_carat_weight,
            minimum_price,
            maximum_price,
            must_be_certified,
            verify_cert_images
        ) = self.pref_values

        comment = cached_clean(comment)
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
            if must_be_certified:
                raise KeyValueError('certifier_aliases', e.args[0])
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

        clarity = cached_clean_upper(clarity)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean_upper(cut_grade))
        price_before_markup = clean(price_before_markup.replace(',', ''))
        if price_before_markup:
            price_before_markup = Decimal(price_before_markup)
            carat_price = price_before_markup / carat_weight
        else:
            price_before_markup = None
            carat_price = None

        try:
            depth_percent = Decimal(str(clean(depth_percent)))
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(table_percent)))
        except InvalidOperation:
            table_percent = 'NULL'

        if girdle_thinnest:
            girdle_thinnest = cached_clean_upper(girdle_thinnest)
            girdle = [girdle_thinnest]
            if girdle_thickest:
                girdle_thickest = cached_clean_upper(girdle_thickest)
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''

        if culet_size and culet_size != 'None':
            culet_size = cached_clean_upper(culet_size)
            culet = [culet_size]
            if culet_condition and culet_condition != 'None':
                culet_condition = cached_clean_upper(culet_condition)
                culet.append(culet_condition)
            culet = ' '.join(culet)
        else:
            culet = ''

        polish = self.grading_aliases.get(cached_clean_upper(polish))
        symmetry = self.grading_aliases.get(cached_clean_upper(symmetry))

        fluorescence = cached_clean_upper(fluorescence)
        fluorescence_id = None
        fluorescence_color_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                #fluorescence_color = fluorescence.replace(abbr.upper(), '')
                break
        fluorescence = fluorescence_id

        if fluorescence_color:
            fluorescence_color = cached_clean_upper(fluorescence_color)
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    break
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id

        measurements = clean(measurements)
        length, width, depth = split_measurements(measurements)

        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

        cert_image = cert_image.strip()
        if not cert_image:
            cert_image = ''
        elif verify_cert_images and cert_image != '' and not url_exists(cert_image):
            cert_image = ''

        if price_before_markup is None:
            raise SkipDiamond('No price specified')

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
            owner,
            cut,
            self.nvl(cut_grade),
            self.nvl(color),
            clarity,
            carat_weight,
            moneyfmt(Decimal(carat_price), curr='', sep=''),
            moneyfmt(Decimal(price), curr='', sep=''),
            self.nvl(certifier),
            cert_num,
            cert_image,
            '', # cert_image_local
            depth_percent,
            table_percent,
            girdle,
            culet,
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence),
            self.nvl(fluorescence_color),
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
