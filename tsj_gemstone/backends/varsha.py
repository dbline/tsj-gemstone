from decimal import Decimal, InvalidOperation
import glob
import json
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



def clean(data, upper=False):
    data = ''.join(CLEAN_RE.findall(data)).strip().replace('\n', ' ').replace('\r', '')
    if upper:
        data = data.upper()

    return data


cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)


def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('|')
        if length > 100 or width > 100 or depth > 100:
            raise ValueError
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth


### = things that are unique to each individual backend

class Backend(CSVBackend):
    infile_glob = os.path.join(settings.FTP_ROOT, 'varshaftp/*.csv')  ###
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/varshasample.csv')  ###

    @property
    def enabled(self):  ### unique only if backend has its own preference
        try:
            return self.backend_module in prefs.get('backend')
        except TypeError:
            return False

    def get_default_filename(self):  ###
        files = sorted(glob.glob(self.infile_glob))
        if len(files):
            fn = files[-1]
        else:
            raise ImportSourceError('No data file for Fischer Diamonds found, aborting import.')
        return fn

    def write_diamond_row(self, line,
                          blank_columns=None):  ### The order of the fields here must match the order in the header of the data file
        if blank_columns:
            line = line[:-blank_columns]
        (
            cut,
            carat_weight,
            color,
            clarity,
            measurements,
            cut_grade,
            certifier,
            price_before_markup,
            unused_rapnet_discount,
            depth_percent,
            table_percent,
            girdle_thinnest,
            girdle_thickest,
            unused_girdle_percent,
            unused_girdle_condition,
            culet_size,
            unused_culet_condition,
            polish,
            symmetry,
            fluorescence,
            fluorescence_color,
            unused_crown_height,
            unused_crown_angle,
            pavilion,
            unused_pavillion_angle,
            unused_treatment,
            laser_inscription,
            comment,
            cert_num,
            cert_image,
            cert_image_local,
            stock_number,
            unused_matched_pair,
            unused_is_pair_separable,
            city,
            state,
            country,
            fancy_color,  #USE!
            fancy_color_intensity,
            fancy_color_overtone,
            unused_parcel_stone_count,
            unused_status,
            unused_allow_raplink_feed,
            unused_rapnet_link,
            unused_extra

        ) = line

        """
        if active != 'Y' or availability != 'G':
            raise SkipDiamond('Diamond is not active')
        """
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

        if fancy_color:
            color = None
            fancy_color = cached_clean(fancy_color.replace('-', ' ').upper())
            try:
                fancy_color_id = self.fancy_colors[fancy_color]
            except KeyError as e:
                raise KeyValueError('fancy_color', e.args[0])
        else:
            fancy_color_id = None
            if color:
                try:
                    color = self.color_aliases[cached_clean(color, upper=True)]
                except KeyError as e:
                    raise KeyValueError('color_aliases', e.args[0])
            else:
                raise SkipDiamond('No valid color found')

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

        certifier = cached_clean(certifier, upper=True)
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

        clarity = cached_clean(clarity, upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        cut_grade = self.grading_aliases.get(cached_clean(cut_grade, upper=True))
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
            girdle_thinnest = cached_clean(girdle_thinnest, upper=True)
            girdle = [girdle_thinnest]
            if girdle_thickest:
                girdle_thickest = cached_clean(girdle_thickest, upper=True)
                girdle.append(girdle_thickest)
            girdle = ' - '.join(girdle)
        else:
            girdle = ''

        if culet_size and culet_size != 'None':
            culet_size = cached_clean(culet_size, upper=True)
            culet = [culet_size]
        else:
            culet = ''

        polish = self.grading_aliases.get(cached_clean(polish, upper=True))
        symmetry = self.grading_aliases.get(cached_clean(symmetry, upper=True))

        fluorescence = cached_clean(fluorescence, upper=True)
        fluorescence_id = None
        fluorescence_color_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                # fluorescence_color = fluorescence.replace(abbr.upper(), '')
                break
        fluorescence = fluorescence_id

        if fluorescence_color:
            fluorescence_color = cached_clean(fluorescence_color, upper=True)
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

        cert_image_local = cert_image_local.strip()
        if not cert_image_local:
            cert_image_local = ''

        """
        lot_num = clean(lot_num)
        if lot_num == 'v360':
            v360_link = 'https://v360.in/viewer4.0/vision360.html?d=' + stock_number + '&surl=https://s4.v360.in/images/company/244/'
            # TODO: Currently set up for London Gold we'll need some prefs for any retailer specific ID's
            v360_image = 'https://v360.in/V360Images.aspx?cid=LondonGold&d=' + stock_number
            data = {'v360_link': v360_link, 'v360_image': v360_image}
        else:
        """
        data = {}

        if laser_inscription:
            data['laser_inscription'] = laser_inscription
            laser_inscription = 't'
        else:
            laser_inscription = 'f'

        if price_before_markup is None:
            raise SkipDiamond('No price specified')

        if minimum_price and price_before_markup < minimum_price:
            raise SkipDiamond('Price before markup is less than the minimum of %s.' % minimum_price)
        if maximum_price and price_before_markup > maximum_price:
            raise SkipDiamond('Price before markup is greater than the maximum of %s.' % maximum_price)

        price = None
        for markup in self.markup_list:
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

        # Order must match struture of tsj_gemstone_diamond table
        ret = self.Row(
            self.added_date,
            self.added_date,
            't',  # active
            self.backend_module,
            '',  # lot_num
            stock_number,
            '',  # owner,
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
            cert_image_local,
            depth_percent,
            table_percent,
            girdle,
            culet,
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence),
            self.nvl(fluorescence_color),
            self.nvl(fancy_color_id),
            self.nvl(fancy_color_intensity_id),
            self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            comment,  # comment,
            city,  # city,
            state,  # state,
            country,  # country,
            'f',  # manmade,
            laser_inscription,
            'NULL',  # rap_date
            '{}', # json.dumps(data),  # data
        )

        return ret
