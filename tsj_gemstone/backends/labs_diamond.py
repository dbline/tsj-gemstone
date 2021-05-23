from decimal import Decimal, InvalidOperation
import logging
import os
import json
import glob
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
# TODO: Need to handle spaces between dimensions
MEASUREMENT_RE = re.compile('[\sxX*-]')

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

def fix_float(might_b_float):
    try:
        as_float = float(might_b_float)
        might_b_float = str(int(as_float))
    except ValueError:
        pass

    return might_b_float

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/labs_diamond.csv')
    infile_glob = os.path.join(settings.FTP_ROOT, 'labs-diamond/*.*')

    @property
    def enabled(self):
        try:
            return self.backend_module in prefs.get('backend')
        except TypeError:
            return False

    def get_default_filename(self):
        files = sorted(glob.glob(self.infile_glob))
        if len(files):
            fn = files[-1]
            logger.info('Importing labs_diamond file "%s"' % fn)
            return fn

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            cut,
            stock_number,
            carat_weight,
            color,
            unused_fancy_color_intensity,
            unused_fancy_color_overtone,
            unused_fancy_color_grade,
            clarity,
            rap_discount,
            carat_price,
            cert_num,
            certifier,
            measurements,
            cut_grade,
            polish,
            symmetry,
            fluorescence,
            table_percent,
            depth_percent,
            girdle,
            video_link,
            culet,
            cert_image,

        ) = line

        (
            minimum_carat_weight,
            maximum_carat_weight,
            minimum_price,
            maximum_price,
            must_be_certified,
            verify_cert_images,
            include_mined,
            include_lab_grown,
        ) = self.pref_values

        (
            show_prices
        ) = self.add_pref_values

        #  comment = cached_clean(comment)
        stock_number = fix_float(clean(stock_number, upper=True))
        manmade = 't'

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
            new_certifier = models.Certifier.objects.using('default').create(name=certifier, abbr=certifier)
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
        except InvalidOperation:
            depth_percent = 'NULL'

        try:
            table_percent = Decimal(str(cached_clean(table_percent)))
        except InvalidOperation:
            table_percent = 'NULL'


        """
        if girdle_thinnest:
            girdle_thinnest = cached_clean(girdle_thinnest, upper=True)
            girdle = [girdle_thinnest]
            if girdle_thickest:
                girdle_thickest = cached_clean(girdle_thickest, upper=True)
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''
        """

        """
        if culet_size and culet_size != 'None':
            culet_size = cached_clean(culet_size, upper=True)
            culet = [culet_size]
            if culet_condition and culet_condition != 'None':
                culet_condition = cached_clean(culet_condition, upper=True)
                culet.append(culet_condition)
            culet = ' '.join(culet)
        else:
            culet = ''
        """

        polish = self.grading_aliases.get(cached_clean(polish, upper=True))
        symmetry = self.grading_aliases.get(cached_clean(symmetry, upper=True))

        fluorescence = cached_clean(fluorescence, upper=True)
        fluorescence_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                # fluorescence_color = fluorescence.replace(abbr.upper(), '')
                break


        """
        if fluorescence_color:
            fluorescence_color = cached_clean(fluorescence_color, upper=True)
            for abbr, id in self.fluorescence_color_aliases.iteritems():
                if fluorescence_color.startswith(abbr.upper()):
                    fluorescence_color_id = id
                    break
            if not fluorescence_color_id: fluorescence_color_id = None
        fluorescence_color = fluorescence_color_id
        """

        """
        if fancy_color:
            fancy_color = cached_clean(fancy_color.replace('-', ' ').lower())
            fancy_color_id = self.fancy_colors.get(fancy_color)
        else:
            fancy_color_id = None

        """

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

        cert_num = fix_float(clean(cert_num))
        if not cert_num:
            cert_num = ''


        """
        if certificate_image:
            cert_image_local = 'tsj_gemstone/certificates/%s' % (certificate_image)
            cert_image = '/media/tsj_gemstone/certificates/%s' % (certificate_image)
        else:
            cert_image_local = ''
            cert_image = ''
        #TODO Need to check for image on ftp and move it to tsj_gemstone/certificates also
        """


        cert_image = cert_image.replace('.net//', '.net/').replace('\\', '/').strip()
        if not cert_image:
            cert_image = ''
        elif verify_cert_images and cert_image != '' and not url_exists(cert_image):
            cert_image = ''

        measurements = clean(measurements)
        length, width, depth = split_measurements(measurements)

        data = {}
        if video_link or 'v360' in video_link:
            data.update({'v360_link': video_link})

        if cert_image and 'v360' in cert_image:
            data.update({'v360_link': cert_image})




        if not show_prices == 'none':
            try:
                carat_price = Decimal(clean(carat_price.replace(',', '')))
            except InvalidOperation:
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
                        price = (price_before_markup * (1 + markup[2] / 100))
                        break
                else:
                    if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                        price = (price_before_markup * (1 + markup[2] / 100))
                        break
        else:
            for markup in self.lab_markup_list:
                if prefs.get('markup') == 'carat_weight':
                    if markup[0] <= carat_weight and markup[1] >= carat_weight:
                        price = (price_before_markup * (1 + markup[2] / 100))
                        break
                else:
                    if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
                        price = (price_before_markup * (1 + markup[2] / 100))
                        break

        if not price:
            if prefs.get('markup') == 'carat_weight':
                raise SkipDiamond(
                    "A diamond markup doesn't exist for a diamond with carat weight of %s." % carat_weight)
            else:
                raise SkipDiamond(
                    "A diamond markup doesn't exist for a diamond with pre-markup price of %s." % price_before_markup)



        # Order must match structure of tsj_gemstone_diamond table
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
            '', # cert_image,
            '', # cert_image_local,
            depth_percent,
            table_percent,
            self.nvl(girdle), #'', #girdle,
            self.nvl(culet), #'', # culet,
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence_id),
            'NULL', #self.nvl(fluorescence_color_id),
            'NULL', #self.nvl(fancy_color_id),
            'NULL', #self.nvl(fancy_color_intensity_id),
            'NULL', #self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            '',  #comment,
            '', #city,
            '', #state,
            '',
            manmade, # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            json.dumps(data), #json.dumps(data), # data
        )

        return ret
