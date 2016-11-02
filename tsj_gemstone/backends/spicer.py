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
# TODO: Need to handle spaces between dimensions
MEASUREMENT_RE = re.compile('[\sxX*-]')

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
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/spicer.csv')
    default_filename = '/glusterfs/ftp_home/spicerftp/spicer.csv'

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            stock_number,
            lot_num,
            t_s,
            description,
            count,
            age,
            cost,
            price,
            margin,
        ) = line

        (
            minimum_carat_weight,
            maximum_carat_weight,
            minimum_price,
            maximum_price,
            must_be_certified,
            verify_cert_images
        ) = self.pref_values

        stock_number = clean(stock_number, upper=True)
        lot_num = clean(lot_num, upper=True)

        """
        {
            'Cut': 'NA',
            'Symmetry': 'Very Good',
            'Color': 'G',
            'Sarine Number': 'NA',
            'Carat': '0.52',
            'Lab': 'WG',
            'Diamond Shape': 'Princess Cut',
            'Cert': '00044',
            'Sarine Template': 'NA',
            'Polish': 'Very Good',
            'Clarity': 'SI1'
        }
        """

        dia = {}
        desc = description.splitlines()
        for line in desc:
            try:
                attr = line.split(': ')
                dia[attr[0]] = attr[1]
            except IndexError:
                continue

        cut = dia['Diamond Shape']
        try:
            cut = self.cut_aliases[cached_clean_upper(cut)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = dia['Carat']
        carat_weight = Decimal(str(cached_clean(carat_weight)))

        color = dia['Color']
        color = self.color_aliases.get(cached_clean_upper(color))

        certifier = dia['Lab']
        certifier = cached_clean_upper(certifier)

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

        clarity = dia['Clarity']
        clarity = cached_clean_upper(clarity)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        try:
            cut_grade = dia['Cut']
            cut_grade = self.grading_aliases.get(cached_clean_upper(cut_grade))
        except KeyError as e:
            raise KeyValueError('cut', e.args[0])

        try:
            price = Decimal(cost.replace(',', ''))
            carat_price = price / carat_weight
        except InvalidOperation:
            carat_price = None

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        polish = dia['Polish']
        polish = self.grading_aliases.get(cached_clean_upper(polish))

        symmetry = dia['Symmetry']
        symmetry = self.grading_aliases.get(cached_clean_upper(symmetry))

        cert_num = dia['Cert']
        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

        depth_percent = None
        table_percent = None
        fluorescence_id = None
        fluorescence_color_id = None
        length = None
        width = None
        depth = None

        # Order must match struture of tsj_gemstone_diamond table
        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active
            self.backend_module,
            lot_num,
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
            self.nvl(depth_percent),
            self.nvl(table_percent),
            '', # girdle,
            '', # culet,
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence_id),
            self.nvl(fluorescence_color_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            '', # comment,
            '', #city,
            '', #state,
            '', #country,
            'NULL', # rap_date
        )

        print ret

        return ret
