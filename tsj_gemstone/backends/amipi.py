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

from .base import LRU_CACHE_MAXSIZE, CSVBackend, SkipDiamond, KeyValueError
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

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/amipi.csv')
    default_filename = os.path.join(settings.FTP_ROOT, 'amipi/amipi_Thinkspace.csv')

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            stock_number,
            cut,
            carat_weight,
            color,
            clarity,
            certifier,
            cut_grade,
            polish,
            symmetry,
            fluorescence,
            depth_percent,
            table_percent,
            unused_list_price,
            unused_cash_price_percent,
            cash_price,
            unused_cash_amount,
            unused_measurements,
            length,
            width,
            depth,
            unused_ratio,
            girdle,
            unused_girdle_from,
            unused_girdle_to,
            culet,
            origin,
            unused_matching,
            unused_matching_sku,
            unused_matching_separable,
            cert_num,
            unused_key_to_symbols,
            comment,
            cert_image,
            laser_inscription,
            unused_shade,
            unused_hearts_arrows,
            fancy_color,
            fancy_color_intensity,
            fancy_color_overtone,
            unused_fancy_color_overtone2,
            unused_crown_angle,
            unused_crown_height,
            unused_pavilion_angle,
            unused_pavilion_depth,
            unused_days_to_ship,
            city,
            state,
            country,
            unused_memo_price_percent,
            unused_memo_price,
            unused_milky,
            unused_eye_clean,
            unused_brand,
            video_url
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

        try:
            depth_percent = Decimal(str(clean(depth_percent)))
            if depth_percent > 100:
                raise InvalidOperation
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(table_percent)))
            if table_percent > 100:
                raise InvalidOperation
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
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                continue
        fluorescence = fluorescence_id

        if fancy_color:
            fancy_color = cached_clean(fancy_color.replace('-', ' ').lower())
            fancy_color_id = self.fancy_colors.get(fancy_color)
        else:
            fancy_color_id = None

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
        cert_image = ''


        if origin != '':
            if not include_lab_grown:
                raise SkipDiamond("Don't include lab-grown")
            else:
                manmade = 't'
        else:
            if not include_mined:
                raise SkipDiamond("Don't include mined")
            else:
                manmade = 'f'

        if laser_inscription:
            laser_inscribed = 't'
        else:
            laser_inscribed = 'f'

        # For now we'll use cash price over memo price, this was recommended
        # Price is per carat, amount is total
        carat_price = clean(cash_price.replace(',', ''))
        if carat_price:
            carat_price = Decimal(carat_price)
        else:
            carat_price = None

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        # Initialize price after all other data has been initialized
        price_before_markup = carat_price * carat_weight

        if minimum_price and price_before_markup < minimum_price:
            raise SkipDiamond('Price before markup is less than the minimum of %s.' % minimum_price)
        if maximum_price and price_before_markup > maximum_price:
            raise SkipDiamond('Price before markup is greater than the maximum of %s.' % maximum_price)

        price = None
        if manmade == 'f' or not self.lab_markup_list:
            for markup in self.markup_list:
                if prefs.get('markup') == 'carat_weight':
                    if markup[0] <= carat_weight and markup[1] >= carat_weight:
                        price = (price_before_markup * (1 + markup[2]/100))
                        break
                else:
                    if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                        price = (price_before_markup * (1 + markup[2]/100))
                        break
        else:
            for markup in self.lab_markup_list:
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
            'NULL', # self.nvl(fluorescence_color_id),
            self.nvl(fancy_color_id),
            self.nvl(fancy_color_intensity_id),
            self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            comment,
            city,
            state,
            country,
            manmade,
            laser_inscribed,
            'NULL', # rap_date
            '{}', # data
        )

        return ret
