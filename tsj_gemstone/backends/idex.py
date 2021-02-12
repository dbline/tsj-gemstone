from decimal import Decimal, InvalidOperation
import io
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
import zipfile

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import LRU_CACHE_MAXSIZE, XMLBackend, XMLHandler, ImportSourceError, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt
from thinkspace.utils.http import url_exists

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    if data is None:
        return ''
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('x')
        if length > 100 or width > 100 or depth > 100:
            raise ValueError
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class IdexHandler(XMLHandler):
    def startElement(self, name, attrs):
        if name != 'item':
            return

        self.backend.try_write_row(self.writer, attrs)

    def endDocument(self):
        if self.backend.row_buffer:
            self.writer.writerows(self.backend.row_buffer)

class Backend(XMLBackend):
    handler_class = IdexHandler

    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/idex.xml')

    @property
    def enabled(self):
        return prefs.get('idex_access_key')

    def get_fp(self):
        if self.filename:
            return open(self.filename, 'rb')

        if settings.DEBUG and not self.nodebug:
            return open(self.debug_filename, 'rb')

        key = prefs.get('idex_access_key')
        if not key:
            # TODO: We shouldn't be able to get here anymore, enabled checks the pref
            logger.error('No IDEX key found')
            return

        data = urllib.urlencode({'String_Access': key, 'Show_Empty': 1})

        url = 'http://idexonline.com/Idex_Feed_API-Full_Inventory'
        try:
            idex_request = Request(url + '?' + data)
        except HTTPError as e:
            raise ImportSourceError(str(e))

        # Response objects don't support seeking, which ZipFile expects
        response = urlopen(idex_request)
        zipbytes = io.BytesIO(response.read())

        if zipbytes.read(5) == '<root':
            zipbytes.seek(0)
            raise ImportSourceError(zipbytes.read())
        zipbytes.seek(0)

        try:
            z = zipfile.ZipFile(zipbytes)
        except Exception:
            import pdb
            pdb.set_trace()
            raise
        fp = z.open(z.infolist()[0])

        return fp

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

        stock_number = clean(data.get('sr'))
        comment = cached_clean(data.get('rm'))
        owner = cached_clean(data.get('sup'))
        try:
            cut = self.cut_aliases[cached_clean(data.get('cut'), upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        carat_weight = Decimal(str(cached_clean(data.get('ct'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        color = self.color_aliases.get(cached_clean(data.get('col'), upper=True))

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

        clarity = cached_clean(data.get('cl'), upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(data.get('mk'), upper=True))
        try:
            carat_price = clean(data.get('ap').replace(',', ''))
            if carat_price:
                carat_price = Decimal(carat_price)
            else:
                carat_price = None
        except AttributeError:
            carat_price = None

        try:
            depth_percent = Decimal(str(clean(data.get('dp'))))
            if depth_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(data.get('tb'))))
            if table_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            table_percent = 'NULL'

        girdle = cached_clean(data.get('gd'), upper=True)
        if not girdle or girdle == '-':
            girdle = ''

        culet = cached_clean(data.get('cs'), upper=True)
        polish = self.grading_aliases.get(cached_clean(data.get('pol'), upper=True))
        symmetry = self.grading_aliases.get(cached_clean(data.get('sym'), upper=True))

        fluorescence = cached_clean(data.get('fl'), upper=True)
        fluorescence_id = None
        fluorescence_color = cached_clean(data.get('fc'), upper=True)
        fluorescence_color_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                continue
        fluorescence = fluorescence_id

        if fluorescence_color:
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    continue
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id

        measurements = clean(data.get('mes'))
        length, width, depth = split_measurements(measurements)

        cert_num = clean(data.get('cn'))
        if not cert_num:
            cert_num = ''

        # TODO: Diamond image is data['ip']

        cert_image = data.get('cp')
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

        state = cached_clean(data.get('st'))
        country = cached_clean(data.get('cty'))

        # TODO: Matching pair stock number is data['psr']

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
            moneyfmt(Decimal(price_before_markup), curr='', sep=''),
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
            comment,
            '', # city,
            state,
            country,
            'f', # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
