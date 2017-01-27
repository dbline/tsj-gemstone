from decimal import Decimal, InvalidOperation
import csv
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
from django.db import connection, transaction
from django.utils.lru_cache import lru_cache

from .base import LRU_CACHE_MAXSIZE, CSVBackend, SkipDiamond, KeyValueError
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

cached_clean = lru_cache(maxsize=LRU_CACHE_MAXSIZE)(clean)

def split_measurements(measurements):
    try:
        length, width, depth = [x for x in MEASUREMENT_RE.split(measurements) if x]
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

one_word = [
    'Lab',
    'Cert',
    'Carat',
    'Color',
    'Clarity',
    'Polish',
    'Symmetry',
    'Cut',
]

two_words = [
    'Diamond Shape',
    'Sarine Number',
    'Sarine Template',
]

class Backend(CSVBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/spicer.csv')
    infile_glob = '/glusterfs/ftp_home/spicerftp/*-INVENTORY.CSV'

    def get_default_filename(self):
        files = sorted(glob.glob(self.infile_glob))
        if len(files):
            fn = files[-1]
            logger.info('Importing Spicer Greene EDGE file "%s"' % fn)
            return fn

    def save(self, fp):
        # fp should be a tempfile.NamedTemporaryFile.  We currently assume
        # that it's also still open in write mode, so flush and reopen.
        fp.flush()
        fp = open(fp.name)

        with transaction.atomic():
            try:
                cursor = connection.cursor()
                cursor.copy_from(fp, 'tsj_gemstone_diamond', null='NULL', columns=self.Row._fields)
            except Exception as e:
                logger.exception("Error on copy_from for %s" % self.backend_module)

        fp.close()

    def _read_rows(self, reader, writer, headers, blank_columns=None):
        existing_sns = set(models.Diamond.objects.filter(source=self.backend_module).values_list('stock_number', flat=True))

        try:
            for line in reader:
                # Sometimes the feed has blank lines
                if not line:
                    continue

                # Rather than fail on malformed CSVs, pad rows which have fewer
                # columns than the header row
                col_diff = (len(headers) - blank_columns) - len(line)
                if col_diff > 0:
                    line.extend([''] * col_diff)

                self.try_write_row(writer, line, blank_columns=blank_columns, existing_sns=existing_sns)
        except csv.Error as e:
            raise ImportSourceError(str(e))

    def try_write_row(self, writer, *args, **kwargs):
        existing_sns = kwargs.pop('existing_sns')

        try:
            diamond_row = self.write_diamond_row(*args, **kwargs)
        except SkipDiamond as e:
            self.import_skip[str(e)] += 1
        except KeyValueError as e:
            self.missing_values[e.key][e.value] += 1
        except KeyError as e:
            self.import_errors[str(e)] += 1
            logger.info('KeyError', exc_info=e)
        except ValueError as e:
            self.import_errors[str(e)] += 1
            logger.info('ValueError', exc_info=e)
        except Exception as e:
            self.import_errors[str(e)] += 1
            logger.error('Diamond import exception', exc_info=e)
        else:
            if diamond_row.stock_number in existing_sns:
                diamond = models.Diamond.objects.get(stock_number=diamond_row.stock_number)
                if diamond_row.active == 't':
                    diamond.active = True
                else:
                    diamond.active = False
                diamond.data = diamond_row.data
                diamond.price = diamond_row.price
                diamond.carat_price = diamond_row.carat_price
                try:
                    diamond.certifier_id = diamond_row.certifier_id
                except:
                    pass
                diamond.save()
            else:
                if len(self.row_buffer) > self.buffer_size:
                    writer.writerows(self.row_buffer)
                    self.row_buffer = [diamond_row]
                else:
                    self.row_buffer.append(diamond_row)
                self.import_successes += 1

    def write_diamond_row(self, line, blank_columns=None):
        if blank_columns:
            line = line[:-blank_columns]
        (
            stock_number,
            vendor,
            lot_num,
            price,
            current,
            image,
            status,
            description,
            category_id,
            category_name,
            category_type,
            category_description,
            lowest_price,
            inventory_type,
            price_method,
            additional_info
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

        if status == 'I':
            status = 't'
        else:
            status = 'f'

        """
        Harmony Loose Diamond With One 0.70Ct Round Brilliant Cut D Si1 Diamond Lab: GIA Cert: 6225820160 Sarine Number: AUPRDJ8M18G Sarine Template: SPRGCHRMD3 Carat: 0.7 Color: D Clarity: SI2 Cut: Very Good Polish: Very Good Symmetry: Very Good Diamond Shape: Oval

        {
            'Symmetry': 'Excellent',
            'Color': 'I',
            'Sarine Number': 'Y2BC0QWA238',
            'Carat': '0.6',
            'Lab': 'GIA',
            'Diamond Shape': 'Round',
            'Cert': '2186348789',
            'Sarine Template': 'SPRGCHRMD3',
            'Polish': 'Very',
            'Clarity': 'VS2'
        }

        """

        dia = {}

        if category_id == '190':
            sections = description.split(': ')
            last_key = None
            for section in sections:
                if last_key:
                    value = section.split()[:1][0]
                    dia[last_key] = value

                key = section.split()[-2:]
                key = ' '.join(key)
                if key in two_words:
                    last_key = key
                else:
                    key = section.split()[-1:][0]
                    if key in one_word:
                        last_key = key
                    else:
                        last_key = None
        else:
            raise SkipDiamond('Not a diamond')

        try:
            cut = dia['Diamond Shape']
            cut = self.cut_aliases[cached_clean(cut, upper=True)]
        except KeyError as e:
            raise KeyValueError('cut_aliases', e.args[0])

        try:
            carat_weight = dia['Carat']
            carat_weight = Decimal(str(cached_clean(carat_weight)))
        except KeyError as e:
            raise KeyValueError('carat_weight', e.args[0])

        color = dia['Color']
        color = self.color_aliases.get(cached_clean(color, upper=True))

        certifier = dia['Lab']
        certifier = cached_clean(certifier, upper=True)

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
        clarity = cached_clean(clarity, upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            raise KeyValueError('clarity', e.args[0])

        try:
            cut_grade = dia['Cut']
            cut_grade = self.grading_aliases.get(cached_clean(cut_grade, upper=True))
        except KeyError as e:
            raise KeyValueError('cut', e.args[0])

        try:
            price = Decimal(price)
            carat_price = price / carat_weight
        except InvalidOperation:
            carat_price = None

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        polish = dia['Polish']
        polish = self.grading_aliases.get(cached_clean(polish, upper=True))

        symmetry = dia['Symmetry']
        symmetry = self.grading_aliases.get(cached_clean(symmetry, upper=True))

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

        data = {}

        try:
            sarine_id = dia['Sarine Number']
            if sarine_id != 'NA':
                data['sarine_id'] = sarine_id
        except KeyError as e:
            raise KeyValueError('sarine_id', e.args[0])

        try:
            sarine_template = dia['Sarine Template']
            if sarine_template != 'NA':
                data['sarine_template'] = sarine_template
        except KeyError as e:
            raise KeyValueError('sarine_template', e.args[0])

        # Order must match struture of tsj_gemstone_diamond table
        ret = self.Row(
            self.added_date,
            self.added_date,
            status, # active
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
            json.dumps(data),
        )

        return ret
