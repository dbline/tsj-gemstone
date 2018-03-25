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
from django.conf import settings

from .base import LRU_CACHE_MAXSIZE, CSVBackend, SkipDiamond, KeyValueError
from .. import models
from ..utils import moneyfmt
from tsj_pointofsale.prefs import prefs as pos_prefs

partial_import = pos_prefs.get('partial_import', True)

FTP_ROOT = os.environ.get('FTP_ROOT', '/glusterfs/ftp_home/')

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

class Backend(CSVBackend):
    def __init__(self, *args, **kwargs):
        super(Backend, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        
        
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/spicer.csv')
    if partial_import:
        infile_glob = os.path.join(FTP_ROOT, 'spicerftp/*-INVENTORY.CSV')
    else:
        infile_glob = os.path.join(FTP_ROOT, 'spicerftp/*-INVENTORY-FULL.CSV')

    @property
    def enabled(self):
        return self.backend_module in prefs.get('polygon_id')

    def get_default_filename(self):
        files = sorted(glob.glob(self.infile_glob))
        if len(files):
            fn = files[-1]
            self.logger.info('Importing Spicer Greene EDGE file "%s"' % fn)
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
                self.logger.exception("Error on copy_from for %s" % self.backend_module)

        fp.close()

    def _read_rows(self, reader, writer, headers, blank_columns=None):
        existing_sns = set(models.Diamond.objects.filter(source=self.backend_module).values_list('stock_number', flat=True))

        if not partial_import:
            # Only mark active discontinued if we're running everything.
            models.Diamond.objects.filter(source=self.backend_module).update(active=False)

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
            #self.logger.info('Skipping Diamond "%s" - SkipDiamond' % repr(e))
        except KeyValueError as e:
            self.missing_values[e.key][e.value] += 1
        except KeyError as e:
            self.import_errors[str(e)] += 1
            self.logger.info('KeyError', exc_info=e)
        except ValueError as e:
            self.import_errors[str(e)] += 1
            self.logger.info('ValueError', exc_info=e)
        except Exception as e:
            self.import_errors[str(e)] += 1
            self.logger.error('Diamond import exception', exc_info=e)
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
                self.logger.info('Updating Existing Diamond "%s"' % diamond_row.stock_number)
            else:
                if len(self.row_buffer) > self.buffer_size:
                    writer.writerows(self.row_buffer)
                    self.row_buffer = [diamond_row]
                else:
                    self.row_buffer.append(diamond_row)
                self.import_successes += 1
                self.logger.info('Adding New Diamond "%s"' % diamond_row.stock_number)

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
            style_number,
            memo,
            cut,
            carat_weight,
            color,
            clarity,
            cut_grade,
            polish,
            symmetry,
            certifier,
            cert_num,
            collection,
            placement,
            length,
            width,
            depth,
            fluorescence,
            v360_link,
            metal_type,
            metal_color,
            title,
            meta_title,
            meta_keywords,
            meta_description,
            desc,
            category
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

        if category_id != '190':
            raise SkipDiamond('Not a diamond')

        try:
            cut = self.cut_aliases[cached_clean(cut, upper=True)]
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Cut Aliases' % stock_number)
            raise KeyValueError('cut_aliases', e.args[0],)


        try:
            carat_weight = Decimal(str(cached_clean(carat_weight)))
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Carat Weight' % stock_number)
            raise KeyValueError('carat_weight', e.args[0])

        color = self.color_aliases.get(cached_clean(color, upper=True))

        certifier = cached_clean(certifier, upper=True)

        try:
            certifier_id, certifier_disabled = self.certifier_aliases[certifier]
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Certifier Aliases' % stock_number)
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
            self.logger.info('Skipping Diamond "%s" - Clarity Aliases' % stock_number)
            raise KeyValueError('clarity', e.args[0])

        try:
            cut_grade = self.grading_aliases.get(cached_clean(cut_grade, upper=True))
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Cut Grade Aliases' % stock_number)
            raise KeyValueError('cut', e.args[0])

        try:
            price = Decimal(price)
            carat_price = price / carat_weight
        except InvalidOperation:
            carat_price = None

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        polish = self.grading_aliases.get(cached_clean(polish, upper=True))
        symmetry = self.grading_aliases.get(cached_clean(symmetry, upper=True))

        fluorescence = cached_clean(fluorescence, upper=True)
        fluorescence_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                #fluorescence_color = fluorescence.replace(abbr.upper(), '')
                break
        fluorescence = fluorescence_id
        fluorescence_color_id = None

        cert_num = clean(cert_num)
        if not cert_num:
            cert_num = ''

        depth_percent = None
        table_percent = None

        data = {}
        if v360_link:
            data.update({'v360_link': v360_link})

        if self.nvl(description):
            if self.nvl(memo):
                data.update({'alt_description': description + memo})
            else:
                data.update({'alt_description': description})

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
            'NULL', # self.nvl(fancy_color_id),
            'NULL', # self.nvl(fancy_color_intensity_id),
            'NULL', # self.nvl(fancy_color_overtone_id),
            self.nvl(length),
            self.nvl(width),
            self.nvl(depth),
            '', # comment,
            '', #city,
            '', #state,
            '', #country,
            'f', # manmade,
            'f', # laser_inscribed,
            'NULL', # rap_date
            json.dumps(data),
        )

        return ret
