from decimal import Decimal, InvalidOperation
import glob
import io
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
import zipfile

from django.conf import settings
from django.utils.functional import memoize

from .base import XMLBackend, XMLHandler, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
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

class ASCHandler(XMLHandler):
    def __init__(self, backend, writer):
        # ContentHandler is an old-style class
        XMLHandler.__init__(self, backend, writer)

        self.key = ''
        self.row = {}

    def startElement(self, name, attrs):
        name = name.encode('utf-8').strip()
        if name:
            self.key = name

    def characters(self, data):
        data = data.encode('utf-8').strip()
        if data:
            self.row[self.key] = data

    def endElement(self, name):
        name = name.encode('utf-8').strip()
        if name != 'ItemNum':
            return

        self.backend.try_write_row(self.writer, self.row)
        self.row = {}

    def endDocument(self):
        if self.backend.row_buffer:
            self.writer.writerows(self.backend.row_buffer)

class Backend(XMLBackend):
    handler_class = ASCHandler

    infile_glob = '/glusterfs/ftp_home/{username}/data/ASC_ITEM_*XML'
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/asc.xml')

    def get_default_filename(self):
        username = prefs.get('asc')

        if not username:
            logger.warning('Missing ASC FTP username, aborting import.')
            return

        fn = max(glob.iglob(self.infile_glob.format(username=username)), key=os.path.getctime)
        if not fn:
            logger.warning('No ASC file for username {}, aborting import.'.format(username))
            return

        return fn

    def write_diamond_row(self, data):
        (
            minimum_carat_weight,
            maximum_carat_weight,
            minimum_price,
            maximum_price,
            must_be_certified,
            verify_cert_images
        ) = self.pref_values

        stock_number = clean(data.get('WEBITEM'))
        try:
            cut = self.cut_aliases[cached_clean_upper(data.get('Stone1Shape'))]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        quantity = int(data.get('TotalQtyOH'))
        if quantity:
            active = 't'
        else:
            active = 'f'
            #raise SkipDiamond('No quantity on hand.')

        flag = cached_clean_upper(data.get('WebItemFlag'))
        if flag == 'I':
            active = 'f'

        carat_weight = Decimal(str(cached_clean(data.get('Stone1Wt'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond("Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight))
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond("Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight))

        color = self.color_aliases.get(cached_clean_upper(data.get('Stone1Color')))

        certifier = cached_clean_upper(data.get('StoneCertLab1'))
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

        clarity = cached_clean_upper(data.get('Stone1Clarity'))
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean_upper(data.get('StoneCutGrade1')))

        try:
            price = clean(data.get('LastCost').replace(',', ''))
            if price:
                price = Decimal(price)
            else:
                price = None
        except AttributeError:
            price = None

        try:
            depth_percent = Decimal(str(clean(data.get('StoneDepthPct1'))))
            if depth_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(data.get('StoneTablePct1'))))
            if table_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            table_percent = 'NULL'

        girdle = cached_clean_upper(data.get('gd'))
        if not girdle or girdle == '-':
            girdle = ''

        culet = cached_clean_upper(data.get('cs'))
        polish = self.grading_aliases.get(cached_clean_upper(data.get('StonePolish1')))
        symmetry = self.grading_aliases.get(cached_clean_upper(data.get('StoneSymmetry1')))

        fluorescence = cached_clean_upper(data.get('StoneFluorescence1')).split()
        fluorescence_id = None
        if fluorescence:
            for name, id in self.fluorescence_aliases.iteritems():
                if name == fluorescence[0]:
                    fluorescence_id = id
                    continue
        fluorescence = fluorescence_id

        fluorescence_color = cached_clean_upper(data.get('fc'))
        fluorescence_color_id = None
        if fluorescence_color:
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    continue
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id

        length = clean(data.get('StoneMmSize1_1'))
        width = clean(data.get('StoneMmSize2_1'))
        depth = clean(data.get('StoneMmSize3_1'))

        cert_num = clean(data.get('CertificateNum'))
        if not cert_num:
            cert_num = ''

        if price is None:
            raise SkipDiamond('No price specified')

        # Initialize price after all other data has been initialized
        # ASC already includes total price
        price_before_markup = price
        carat_price = price / carat_weight

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

        ret = self.Row(
            self.added_date,
            self.added_date,
            active, # active
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
            self.nvl(certifier),
            cert_num,
            '', # cert_image
            '', # cert_image_local
            depth_percent,
            table_percent,
            '', # girdle
            '', # culet
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence_id),
            'NULL', # self.nvl(fluorescence_color_id)
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            '', # comment
            '', # city
            '', # state
            '', # country
            'NULL' # rap_date
        )

        return ret
