from collections import defaultdict, namedtuple
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import io
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import tempfile
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError
import xml.sax
import zipfile

from django.conf import settings
from django.db import connection, transaction
from django.utils.functional import memoize

from .base import BaseBackend, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))

INFILE_GLOB = '/glusterfs/ftp_home/orrsftp/data/ASC_ITEM_*XML'
SOURCE_NAME = 'asc'

Row = namedtuple('Row', (
    'created',
    'modified',
    'active',
    'source',
    'lot_num',
    'stock_number',
    'owner',
    'cut_id',
    'cut_grade_id',
    'color_id',
    'clarity_id',
    'carat_weight',
    'carat_price',
    'price',
    'certifier_id',
    'cert_num',
    'cert_image',
    'cert_image_local',
    'depth_percent',
    'table_percent',
    'girdle',
    'culet',
    'polish_id',
    'symmetry_id',
    'fluorescence_id',
    'fluorescence_color_id',
    'length',
    'width',
    'depth',
    'comment',
    'city',
    'state',
    'country',
    'rap_date'
))

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

class ASCHandler(xml.sax.ContentHandler):
    def __init__(self, writer, missing_values, import_successes, import_errors, import_skip):
        # ContentHandler is an old-style class
        xml.sax.ContentHandler.__init__(self)

        # Passed in from Backend.run so that we can still access them there
        self.writer, self.missing_values, self.import_successes, self.import_errors, self.import_skip = writer, missing_values, import_successes, import_errors, import_skip

        self.cut_aliases = models.Cut.objects.as_dict()
        self.color_aliases = models.Color.objects.as_dict()
        self.clarity_aliases = models.Clarity.objects.as_dict()
        self.grading_aliases = models.Grading.objects.as_dict()
        self.fluorescence_aliases = models.Fluorescence.objects.as_dict()
        self.fluorescence_color_aliases = models.FluorescenceColor.objects.as_dict()
        self.certifier_aliases = models.Certifier.objects.as_dict_disabled()

        self.markup_list = models.DiamondMarkup.objects.values_list('start_price', 'end_price', 'percent')

        # We want all the imported records to have the same added_date
        self.added_date = datetime.now()

        # Preload prefs that write_diamond_row needs to filter out diamonds
        self.pref_values = (
            Decimal(prefs.get('rapaport_minimum_carat_weight', '0')),
            Decimal(prefs.get('rapaport_maximum_carat_weight', '0')),
            Decimal(prefs.get('rapaport_minimum_price', '0')),
            Decimal(prefs.get('rapaport_maximum_price', '0')),
            prefs.get('rapaport_must_be_certified', True),
            prefs.get('rapaport_verify_cert_images', False),
        )

        # To cut down on disk writes, we buffer the rows
        self.row_buffer = []
        self.buffer_size = 1000

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
        try:
            diamond_row = write_diamond_row(
                self.row,
                self.cut_aliases,
                self.color_aliases,
                self.clarity_aliases,
                self.grading_aliases,
                self.fluorescence_aliases,
                self.fluorescence_color_aliases,
                self.certifier_aliases,
                self.markup_list,
                self.added_date,
                self.pref_values,
            )
        except SkipDiamond as e:
            self.import_skip += 1
            #logger.info('SkipDiamond: %s' % e.message)
            return
        except KeyValueError as e:
            self.missing_values[e.key].add(e.value)
        except KeyError as e:
            self.import_errors += 1
            logger.info('KeyError', exc_info=e)
        except ValueError as e:
            self.import_errors += 1
            logger.info('ValueError', exc_info=e)
        except Exception as e:
            # Create an error log entry and increment the import_errors counter
            #import_error_log_details = str(line) + '\n\nTOTAL FIELDS: ' + str(len(line)) + '\n\nTRACEBACK:\n' + traceback.format_exc()
            #if import_log: ImportLogEntry.objects.create(import_log=import_log, csv_line=reader.line_num, problem=str(e), details=import_error_log_details)
            self.import_errors += 1
            logger.error('Diamond import exception', exc_info=e)
        else:
            if len(self.row_buffer) > self.buffer_size:
                self.writer.writerows(self.row_buffer)
                self.row_buffer = []
            else:
                self.row_buffer.append(diamond_row)
            self.import_successes += 1

        self.row = {}

    def endDocument(self):
        if self.row_buffer:
            self.writer.writerows(self.row_buffer)

class Backend(BaseBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/asc.xml')

    def get_default_filename(self):
        files = sorted(glob.glob(INFILE_GLOB))
        if len(files):
            fn = files[-1]
            logger.info('Importing ASC file "%s"' % fn)
            return fn

    def run(self):
        fp = self.get_fp()
        if not fp:
            return 0, 1

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % SOURCE_NAME)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        import_successes = 0
        import_errors = 0
        import_skip = 0

        # TODO: We shouldn't need KeyError or ValueError if we're correctly
        #       accounting for the possible failure conditions with SkipDiamond
        #       and KeyValueError.
        missing_values = defaultdict(set)

        ASCParser = xml.sax.make_parser()
        ASCParser.setContentHandler(ASCHandler(
            writer, missing_values, import_successes, import_errors, import_skip
        ))
        ASCParser.parse(fp)

        tmp_file.flush()
        tmp_file = open(tmp_file.name)

        with transaction.commit_manually():
            # FIXME: Don't truncate/replace the table if the import returned no data
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM tsj_gemstone_diamond WHERE source='%s'" % SOURCE_NAME)
                cursor.copy_from(tmp_file, 'tsj_gemstone_diamond', null='NULL', columns=Row._fields)
            except Exception as e:
                transaction.rollback()
                raise
            else:
                transaction.commit()

        tmp_file.close()

        if missing_values:
            for k, v in missing_values.items():
                import_errors += 1
                self.report_missing_values(k, v)

        if import_skip:
            self.report_skipped_diamonds(import_skip)

        return import_successes, import_errors

# TODO: Move somewhere more general
def nvl(data):
    if data is None or data == '':
        return 'NULL'
    return data

def write_diamond_row(data, cut_aliases, color_aliases, clarity_aliases, grading_aliases, fluorescence_aliases, fluorescence_color_aliases, certifier_aliases, markup_list, added_date, pref_values):
    minimum_carat_weight, maximum_carat_weight, minimum_price, maximum_price, must_be_certified, verify_cert_images = pref_values

    stock_number = clean(data.get('WEBITEM'))
    try:
        cut = cut_aliases[cached_clean_upper(data.get('Stone1Shape'))]
    except KeyError as e:
        raise KeyValueError('cut_aliases', e.args[0])

    carat_weight = Decimal(str(cached_clean(data.get('Stone1Wt'))))
    if carat_weight < minimum_carat_weight:
        raise SkipDiamond("Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight))
    elif maximum_carat_weight and carat_weight > maximum_carat_weight:
        raise SkipDiamond("Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight))

    color = color_aliases.get(cached_clean_upper(data.get('Stone1Color')))

    certifier = cached_clean_upper(data.get('StoneCertLab1'))
    # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
    if must_be_certified:
        if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
            raise SkipDiamond('No valid Certifier was specified.')
    try:
        certifier_id, certifier_disabled = certifier_aliases[certifier]
    except KeyError as e:
        #raise KeyValueError('certifier_aliases', e.args[0])
        certifier_id = None
        certifier_disabled = False

    if certifier_disabled:
        raise SkipDiamond('Certifier disabled')

    if certifier and not certifier_id:
        new_certifier = models.Certifier.objects.create(name=certifier, abbr=certifier)
        certifier_aliases.update({certifier: (int(new_certifier.id), new_certifier.disabled)})
        certifier = new_certifier.pk
    else:
        certifier = certifier_id

    clarity = cached_clean_upper(data.get('Stone1Clarity'))
    if not clarity:
        raise SkipDiamond('No clarity specified')
    try:
        clarity = clarity_aliases[clarity]
    except KeyError as e:
        raise KeyValueError('clarity', e.args[0])

    cut_grade = grading_aliases.get(cached_clean_upper(data.get('StoneCutGrade1')))

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
    polish = grading_aliases.get(cached_clean_upper(data.get('StonePolish1')))
    symmetry = grading_aliases.get(cached_clean_upper(data.get('StoneSymmetry1')))

    fluorescence = cached_clean_upper(data.get('StoneFluorescence1'))
    fluorescence_id = None
    fluorescence_color = cached_clean_upper(data.get('fc'))
    fluorescence_color_id = None
    for abbr, id in fluorescence_aliases.iteritems():
        if fluorescence.startswith(abbr.upper()):
            fluorescence_id = id
            continue
    fluorescence = fluorescence_id

    if fluorescence_color:
        for abbr, id in fluorescence_color_aliases.iteritems():
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
    for markup in markup_list:
        if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
            price = (price_before_markup * (1 + markup[2]/100))
            break
    if not price:
        raise SkipDiamond("A diamond markup doesn't exist for a diamond with pre-markup price of '%s'." % price_before_markup)

    ret = Row(
        added_date,
        added_date,
        't', # active
        SOURCE_NAME,
        '', # lot_num
        stock_number,
        '', # owner
        cut,
        nvl(cut_grade),
        nvl(color),
        clarity,
        carat_weight,
        moneyfmt(Decimal(carat_price), curr='', sep=''),
        moneyfmt(Decimal(price), curr='', sep=''),
        nvl(certifier),
        cert_num,
        '', # cert_image
        '', # cert_image_local
        depth_percent,
        table_percent,
        '', # girdle
        '', # culet
        nvl(polish),
        nvl(symmetry),
        nvl(fluorescence_id),
        'NULL', # nvl(fluorescence_color_id)
        nvl(length),
        nvl(width),
        nvl(depth),
        '', # comment
        '', # city
        '', # state
        '', # country
        'NULL' # rap_date
    )

    return ret
