import csv
from decimal import Decimal, InvalidOperation
import logging
import os
import random
import re
from string import ascii_letters, digits, whitespace, punctuation
import tempfile
import time

from lxml import etree
import requests
import zeep

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import (LRU_CACHE_MAXSIZE, BaseBackend, ImportSourceError,
                   KeyValueError, SkipDiamond)
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

RAPNET_WSDL = 'https://technet.rapaport.com/WebServices/RetailFeed/Feed.asmx?WSDL'

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

def clean(data, upper=False):
    if data is None:
        return ''
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)


class Backend(BaseBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/rapnet.xml')

    @property
    def enabled(self):
        username = prefs.get('rapaport_username')
        password = prefs.get('rapaport_password')
        version = prefs.get('rapaport_version')
        return username and password and version == 'rapnetii'

    def get_data(self):
        doc = None
        data = []

        if self.filename:
            doc = etree.parse(open(self.filename, 'rb'))

        # TODO: We should put a couple paginated XML files in ../tests/data
        #       so that we can run through the loop below when debugging
        if settings.DEBUG and not self.nodebug:
            doc = etree.parse(open(self.debug_filename, 'rb'))

        if doc:
            for obj in doc.xpath('//Table1'):
                data.append(dict(((e.tag, e.text) for e in list(obj.iterchildren()))))
            return data

        username = prefs.get('rapaport_username')
        password = prefs.get('rapaport_password')

        client = zeep.Client(wsdl=RAPNET_WSDL)
        try:
            response = client.service.Login(username, password)
            print ("response",response)
        except zeep.exceptions.Fault as e:
            # Try to extract a human friendly string from the exception. For example, an auth error:
            # System.Web.Services.Protocols.SoapException: Server was unable to process request. ---> System.Security.SecurityException: You are not authenticated for RapNet InventoryLink web service.
            #   at Feed.Login(String Username, String Password)
            #   --- End of inner exception stack trace ---
            full_exc_str = str(e)
            exc_str = full_exc_str[full_exc_str.find('---> ')+5:].split('\n', 1)[0]
            logger.exception('RapNet SOAP error')
            raise ImportSourceError('RapNet SOAP error {}'.format(exc_str).strip())
        else:
            ticket = response['header']['AuthenticationTicketHeader']['Ticket']

        factory = client.type_factory('ns0')
        params = {
    #        'ShapeCollection': [],
    #        'LabCollection': [],
    #        'FluorescenceColorsCollection': [],
    #        'FluorescenceIntensityCollection': [],
    #        'CuletSizesCollection': [],
    #        'FancyColorCollection': [],
    #        'ColorFrom': '',
            'PageNumber': '1', # Int?
            'PageSize': '50', #  50 is the max!
    #        'ColorTo': '',
    #        'SearchType': 'WHITE', # FANCY and "WHITE or FANCY" are also valid
    #        'FancyColorIntensityFrom': '',
    #        'FancyColorIntensityTo': '',
    #        'ClarityFrom': '',
    #        'ClarityTo': '',
    #        'PolishFrom': '',
    #        'PolishTo': '',
    #        'SymmetryFrom': '',
    #        'SymmetryTo': '',
    #        'GirdleSizeMin': '',
    #        'GirdleSizeMax': '',
    #        'SizeFrom': '',
    #        'SizeTo': '',
    #        'PriceFrom': '',
    #        'PriceTo': '',
    #        'DepthPercentFrom': '',
    #        'DepthPercentTo': '',
    #        'TablePercentFrom': '',
    #        'TablePercentTo': '',
    #        'MeasLengthFrom': '',
    #        'MeasLengthTo': '',
    #        'MeasWidthFrom': '',
    #        'MeasWidthTo': '',
    #        'MeasDepthFrom': '',
    #        'MeasDepthTo': '',
            'SortDirection': 'ASC', # Or DESC
            'SortBy': 'SIZE', # PRICE SHAPE SIZE COLOR CLARITY CUT LAB
        }

        search_prefs = {
            'PriceFrom': prefs.get('rapaport_minimum_price'),
            'PriceTo': prefs.get('rapaport_maximum_price'),
            'SizeFrom': prefs.get('rapaport_minimum_carat_weight'),
            'SizeTo': prefs.get('rapaport_maximum_carat_weight'),
        }
        for k, v in search_prefs.items():
            if v:
                params[k] = v

        headers = {
            'AuthenticationTicketHeader': factory.AuthenticationTicketHeader(*[ticket]),
        }

        ids = set()

        # Accumulate paginated diamond data into ret
        loop_try = 0
        while True:
            new_ids = 0
            page_data = []

            response = client.service.GetDiamonds(
                SearchParams=factory.FeedParameters(**params),
                DiamondsFound=0,
                _soapheaders=headers,
            )
            #  print factory.FeedParameters(**params)
            #  print headers
            doc = response['GetDiamondsResult']['_value_1']
            for obj in doc.xpath('//Table1'):
                page_data.append(dict(((e.tag, e.text) for e in list(obj.iterchildren()))))

            if not page_data:
                print ("break on no 'page_data' - page number: ", params['PageNumber'])
                if loop_try == 4:
                    print ("4 empty pages in a row - breaking out of data download ")
                    break
                print ("trying again: ", loop_try)
                loop_try +=1
                #  params['PageNumber'] = int(params['PageNumber']) + 1
                continue

            for row in page_data:
                if row['DiamondID'] not in ids:
                    ids.add(row['DiamondID'])
                    new_ids += 1
                    data.append(row)

            # If there aren't any new serial numbers, we're probably in an infinite loop
            if not new_ids:
                logger.warning('RapNet infinite loop (diamond count {})'.format(len(ids)))
                print ("Break on no 'new_ids'")
                break

            params['PageNumber'] = int(params['PageNumber']) + 1

            # Spread requests out a bit.  We're not sure what sort of rate
            # limiting the new API will bring with it.
            time.sleep(random.random()*.05)
            print("completed sleep cycle - current data length: ", len(data), "page number: ", params['PageNumber'])

        return data

    def _run(self):
        data = self.get_data()

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        for row in data:
            self.try_write_row(writer, row)

        if self.row_buffer:
            writer.writerows(self.row_buffer)

        return tmp_file

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

        stock_number = clean(str(data.get('DiamondID')), upper=True)

        try:
            cut = self.cut_aliases[cached_clean(data.get('ShapeTitle'), upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(data.get('CutLongTitle'), upper=True))
        color = self.color_aliases.get(cached_clean(data.get('ColorTitle'), upper=True))

        clarity = cached_clean(data.get('ClarityTitle'), upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        carat_weight = Decimal(cached_clean(str(data.get('Weight'))))
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)
        elif maximum_carat_weight and carat_weight > maximum_carat_weight:
            raise SkipDiamond('Carat weight is greater than the maximum of %s.' % maximum_carat_weight)

        # TODO: There are TotalSalesPriceInCurrency and CurrencySymbol keys
        #       which may be useful if a retailer specifies a non-USD currency?
        carat_price = Decimal(data['FinalPrice']) * Decimal(data['Weight'])
        price_before_markup = Decimal(data['FinalPrice'])

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

        certifier = cached_clean(data.get('LabTitle'), upper=True)
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

        cert_num = clean(data.get('CertificateNumber'))
        if not cert_num:
            cert_num = ''

        # TODO: Is there a reliable URL we can use to construct a URL?
        #       There's a HasCertFile key which must be relevant..
        cert_image = ''

        try:
            depth_percent = Decimal(clean(str(data.get('DepthPercent'))))
            if depth_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(cached_clean(str(data.get('TablePercent'))))
            if table_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            table_percent = 'NULL'

        if data.get('GirdleSizeMin'):
            girdle_thinnest = cached_clean(data['GirdleSizeMin'])
            girdle = [girdle_thinnest]
            if data.get('GirdleSizeMax'):
                girdle_thickest = cached_clean(data['GirdleSizeMax'])
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''

        culet = cached_clean(data.get('CuletSizeTitle'))
        polish = self.grading_aliases.get(cached_clean(data.get('PolishTitle'), upper=True))
        symmetry = self.grading_aliases.get(cached_clean(data.get('SymmetryTitle'), upper=True))

        fluorescence_id = None
        # TODO: No fluorescence_color in the feed?
        fluorescence_color_id = None
        fl = data.get('FluorescenceIntensityTitle', '')
        if fl:
            fluorescence = cached_clean(fl, upper=True)
            for abbr, id in self.fluorescence_aliases.iteritems():
                if fluorescence.startswith(abbr.upper()):
                    fluorescence_id = id
                    continue

        length = data.get('MeasLength')
        width = data.get('MeasWidth')
        depth = data.get('MeasDepth')

        owner = data.get('SellerID')
        lot_num = data.get('VendorStockNumber')

        ret = self.Row(
            self.added_date,
            self.added_date,
            't', # active
            self.backend_module,
            lot_num,
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
            'NULL', # self.nvl(fancy_color_id),
            'NULL', # self.nvl(fancy_color_intensity_id),
            'NULL', # self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            '', # comment,
            '', # city,
            '', # state,
            '', # country,
            'f', # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
