from decimal import Decimal, InvalidOperation
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
from urlparse import urlparse

from django.conf import settings
from django.utils.lru_cache import lru_cache

from .base import LRU_CACHE_MAXSIZE, CSVBackend, ImportSourceError, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt
from thinkspace.utils.http import url_exists

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))
# Formats we've seen: 5x2x3, 5*2*3, 5-2x3
MEASUREMENT_RE = re.compile('[x*-]')

def clean(data, upper=False):
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

def split_measurements(measurements):
    try:
        length, width, depth = MEASUREMENT_RE.split(measurements)
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/rapnet-1.0.csv')

    @property
    def enabled(self):
        username = prefs.get('rapaport_username')
        password = prefs.get('rapaport_password')
        version = prefs.get('rapaport_version')
        return username and password and version == 'rapnet10'

    def get_fp(self):
        if self.filename:
            return open(self.filename, 'rU')

        if settings.DEBUG and not self.nodebug:
            return open(self.debug_filename, 'rU')

        username = prefs.get('rapaport_username')
        password = prefs.get('rapaport_password')

        if not username or not password:
            # TODO: We shouldn't be able to get here anymore, enabled requires both fields
            logger.warning('Missing rapaport credentials, aborting import.')
            return

        # Post the username and password to the auth_url and save the resulting ticket
        auth_url = 'https://technet.rapaport.com/HTTP/Authenticate.aspx'
        auth_data = urllib.urlencode({
            'username': username,
            'password': password})
        auth_request = Request(auth_url, auth_data)
        try:
            ticket = urlopen(auth_request).read()
        except HTTPError as e:
            raise ImportSourceError(str(e))

        # Download the CSV
        url = 'http://technet.rapaport.com/HTTP/DLS/GetFile.aspx'
        data = urllib.urlencode({
            'ticket': ticket
        })
        rap_list_request = Request(url + '?' + data)

        rap_list = urlopen(rap_list_request)

        """ create a tmp file of the rap download for debuging testing purposes
        with open('/tmp/rap.txt', 'wb') as f:
            for l in rap_list:
                f.write(l)

        rap_list = open('/tmp/rap.txt')
        """
        return rap_list

    def _get_headers(self, reader):
        # When we have a valid rapnet account but the user doesn't have DLS,
        # rather than an error response code we receive this string in the
        # response body, which is parsed as a valid CSV:
        # You are not authorized to use the Download Listings Service (DLS), this service requires a RapNet + DLS subscription.
        headers = reader.next()
        if len(headers) and 'not authorized' in headers[0].lower():
            raise ImportSourceError(','.join(headers))
        return headers

    def write_diamond_row(self, line, blank_columns=None):
        (
            owner, # seller in CSV
            unused_owner_account_id, # seller id in CSV
            unused_owner_code, # seller code in CSV
            cut, # shape in CSV
            carat_weight,
            color,
            clarity,
            unused_fancy_color,
            unused_fancy_intensity,
            unused_fancy_overtone,
            cut_grade, #Cut in CSV
            polish,
            symmetry,
            fluorescence,
            unused_fluorescence_intensity,
            measurements,
            unused_meas_length,
            unused_meas_width,
            unused_meas_depth,
            unused_ratio,
            certifier, # lab in CSV
            cert_num,
            stock_number,
            make, # treatment in CSV
            carat_price, # rapnet price in CSV
            rap_percent, # rapnet discount price in CSV
            unused_total_price,
            unused_cash_carat_price,
            unused_cash_percent,
            unused_cash_total_price,
            unused_availability,
            depth_percent,
            table_percent,
            girdle,
            unused_girdle_min,
            unused_girdle_max,
            culet,
            unused_culet_size,
            unused_culet_condition,
            unused_crown,
            unused_pavilion,
            comment,
            unused_member_comments,
            city,
            state,
            country,
            unused_is_matched_pair,
            unused_is_matched_pair_separable,
            unused_pair_stock_number,
            num_stones,
            cert_image,
            unused_image_url,
            unused_rapspec,
            rap_date,
            unused_external_image,
            unused_milky,
            unused_black_inclusion,
            unused_center_inclusion,
            unused_shade,
            unused_key_to_symbols,
            unused_report_issue_date,
            unused_report_type,
            unused_lab_location,
            unused_brand,
            unused_clarity_enhanced,
            unused_color_enhanced,
            unused_hpht,
            unused_irradiated,
            unused_laser_drilled,
            unused_other_treatment,
            unused_pavilion_depth,
            unused_pavilion_angle,
            unused_table_percent,
            unused_supplier_country,
            unused_depth_percent,
            unused_crown_angle,
            unused_crown_height,
            unused_laser_inscription,
            unused_girdle_condition,
            lot_num
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

        lot_num = clean(lot_num)
        owner = cached_clean(owner)
        # Rapnet has started putting the literal value 'null' in the comment field
        """
        if comment.strip() == 'null':
            comment = ''
        comment = cached_clean(comment)
        """
        comment = ''
        stock_number = clean(stock_number, upper=True)
        from dateutil.parser import parse
        rap_date = parse(clean(rap_date))
        #rap_date = datetime(*strptime(clean(rap_date), '%m/%d/%Y %I:%M:%S %p')[0:6])
        city = cached_clean(city)
        state = cached_clean(state)
        country = cached_clean(country)

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
        carat_price = clean(carat_price)
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

        measurements = clean(measurements)
        length, width, depth = split_measurements(measurements)

        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

        cert_image = cert_image.replace('.net//', '.net/').replace('\\', '/').strip()
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

        # Order must match struture of tsj_gemstone_diamond table
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
            self.nvl(fluorescence),
            self.nvl(fluorescence_color),
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
            rap_date, # rap_date
            '{}', # data
        )

        return ret
