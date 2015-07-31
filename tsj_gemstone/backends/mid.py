from collections import defaultdict, namedtuple
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
import os
import re
import six
from string import ascii_letters, digits, whitespace, punctuation
import tempfile
from time import strptime

import requests

from django.conf import settings
from django.db import connection, transaction
from django.utils.functional import memoize

from .base import BaseBackend, SkipDiamond, KeyValueError
from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

CLEAN_RE = re.compile('[%s%s%s%s]' % (punctuation, whitespace, ascii_letters, digits))
# TODO: Need to handle spaces between dimensions
MEASUREMENT_RE = re.compile('[\sx*-]')

SOURCE_NAME = 'mid'

# Order must match struture of tsj_gemstone_diamond table with the exception
# of the id column which is excluded when doing an import.
Row = namedtuple('Row', (
    #'id',
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
    'rap_date',
    'manmade'))

def clean(data, upper=False):
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

def split_measurements(measurements):
    try:
        length, width, depth = [x for x in MEASUREMENT_RE.split(measurements) if x]
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(BaseBackend):
    # This is for development only. Load a much smaller version of the diamonds database from the tests directory.
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/mid.csv')

    def get_fp(self):
        if self.filename:
            return open(self.filename, 'rb')

        if settings.DEBUG and not self.nodebug:
            return open(self.debug_filename, 'rb')

        # TODO: Do we need a feed per-site?
        #url = prefs.get('mid_api_url')
        #if not url:
        #    logger.warning('Missing MID API URL, aborting import.')
        #    return

        url = "https://api.midonline.com/api/QueryApi/GetInventory?q=qqR9BP3NvbZ3oYopkxLjXA%3d%3d"

        # TODO: Catch HTTP errors
        response = requests.get(url)

        return six.moves.cStringIO(response.content)

    def run(self):
        fp = self.get_fp()
        # TODO: Raise exception, don't treat return value as success/failure
        if not fp:
            return 0, 1

        reader = csv.reader(fp)

        headers = reader.next()
        blank_columns = 0
        # Count empty columns on the end
        for col in headers:
            if not col:
                blank_columns += 1

        # Prepare a temp file to use for writing our output CSV to
        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % SOURCE_NAME)
        #writer = csv.writer(tmp_file, quoting=csv.QUOTE_MINIMAL, doublequote=True, escapechar='\\', lineterminator='\n')
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        # PROCEDURE:
        #  1. Load Rapnet CSV into temp file, and lot numbers into Python list.
        #  2. Make list of PKs corresponding to lot numbers in the DB which should
        #     be cleared because they're not in the CSV _and_ they don't exist in
        #     anybody's jewelryboxes.
        #  3. Make list of PKs corresponding to lot numbers in the DB which should
        #     be set inactive because they're not in the CSV and they _do_ exist in
        #     people's jewelryboxes.
        #  4. In a transaction:
        #     - Clear records to delete
        #     - Set status on inactive records
        #     - copy_from() new data in temp file

        # Prepare some needed variables
        import_successes = 0
        import_errors = 0
        import_skip = 0

        cut_aliases = models.Cut.objects.as_dict()
        color_aliases = models.Color.objects.as_dict()
        clarity_aliases = models.Clarity.objects.as_dict()
        grading_aliases = models.Grading.objects.as_dict()
        fluorescence_aliases = models.Fluorescence.objects.as_dict()
        fluorescence_color_aliases = models.FluorescenceColor.objects.as_dict()
        certifier_aliases = models.Certifier.objects.as_dict_disabled()

        markup_list = models.DiamondMarkup.objects.values_list('start_price', 'end_price', 'percent')

        # We want all the imported records to have the same added_date
        added_date = datetime.now()

        # Preload prefs that write_diamond_row needs to filter out diamonds
        # TODO: Do we have a way to send pref values to GN, or do we do all the
        #       filtering locally?
        pref_values = (
            Decimal(prefs.get('rapaport_minimum_carat_weight', '0')),
            Decimal(prefs.get('rapaport_maximum_carat_weight', '0')),
            Decimal(prefs.get('rapaport_minimum_price', '0')),
            Decimal(prefs.get('rapaport_maximum_price', '0')),
            prefs.get('rapaport_must_be_certified', True),
            prefs.get('rapaport_verify_cert_images', False),
        )

        # To cut down on disk writes, we buffer the rows
        row_buffer = []
        buffer_size = 1000

        # TODO: We shouldn't need KeyError or ValueError if we're correctly
        #       accounting for the possible failure conditions with SkipDiamond
        #       and KeyValueError.
        missing_values = defaultdict(set)
        for line in reader:
            try:
                diamond_row = write_diamond_row(
                    line,
                    cut_aliases,
                    color_aliases,
                    clarity_aliases,
                    grading_aliases,
                    fluorescence_aliases,
                    fluorescence_color_aliases,
                    certifier_aliases,
                    markup_list,
                    added_date,
                    pref_values,
                    blank_columns=blank_columns,
                )
            except SkipDiamond as e:
                import_skip += 1
                #logger.info('SkipDiamond: %s' % e.message)
                continue
            except KeyValueError as e:
                missing_values[e.key].add(e.value)
            except KeyError as e:
                import_errors += 1
                logger.info('KeyError', exc_info=e)
            except ValueError as e:
                import_errors += 1
                logger.info('ValueError', exc_info=e)
            except Exception as e:
                # Create an error log entry and increment the import_errors counter
                #import_error_log_details = str(line) + '\n\nTOTAL FIELDS: ' + str(len(line)) + '\n\nTRACEBACK:\n' + traceback.format_exc()
                #if import_log: ImportLogEntry.objects.create(import_log=import_log, csv_line=reader.line_num, problem=str(e), details=import_error_log_details)
                import_errors += 1
                logger.error('Diamond import exception', exc_info=e)
                break
            else:
                if len(row_buffer) > buffer_size:
                    writer.writerows(row_buffer)
                    row_buffer = []
                else:
                    row_buffer.append(diamond_row)
                import_successes += 1

        if row_buffer:
            writer.writerows(row_buffer)

        tmp_file.flush()
        tmp_file = open(tmp_file.name)

        with transaction.commit_manually():
            # FIXME: Don't truncate/replace the table if the import returned no data
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM tsj_gemstone_diamond WHERE source=%s", (SOURCE_NAME,))
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
    if data is None:
        return 'NULL'
    return data

def write_diamond_row(line, cut_aliases, color_aliases, clarity_aliases, grading_aliases, fluorescence_aliases, fluorescence_color_aliases, certifier_aliases, markup_list, added_date,
                      pref_values, blank_columns=None):
    if blank_columns:
        line = line[:-blank_columns]

    # Order must match structure of CSV spreadsheet
    (
        owner,
        unused_feed_date,
        availability, # "Guaranteed Available"
        stock_number, # StockName in CSV
        cert_num,
        unused_is_new_arrival,
        unused_parcel_units,
        unused_location,
        country,
        city,
        state,
        cut,
        carat_weight,
        color,
        clarity,
        certifier,
        unused_fancy_color_fullname,
        unused_fancy_color_intensity,
        unused_fancy_color_overtone,
        unused_fancy_color,
        cut_grade,
        polish,
        symmetry,
        fluorescence,
        fluorescence_color,
        length,
        width,
        depth,
        u_measurements,
        depth_percent,
        table_percent,
        unused_crown_height,
        unused_crown_angle,
        unused_pavilion_depth,
        unused_pavilion_angle,
        u_girdle_thin,
        u_girdle_thick,
        u_girdle_condition,
        u_girdle_percent,
        girdle,
        culet,
        unused_culet_condition,
        comment,
        unused_treatment,
        unused_laser_inscription,
        u_clarity_description,
        u_shade,
        u_milky,
        u_black_inclsion,
        u_central_inclusion,
        u_verification_url,
        cert_image,
        u_diamond_image,
        u_discount,
        u_total_price,
        carat_price,
        u_rap_price,
        u_cert_filename,
        u_image_filename,
        u_allow_on_rap,
        unused_is_matched_pair,
        unused_matching_stock_number,
        unused_is_matched_pair_separable,
    ) = line

    minimum_carat_weight, maximum_carat_weight, minimum_price, maximum_price, must_be_certified, verify_cert_images = pref_values

    # TODO: Until we have prefs
    minimum_carat_weight = 0
    maximum_carat_weight = None
    minimum_price = 0
    maximum_price = False
    must_be_certified = True

    comment = cached_clean(comment)
    stock_number = clean(stock_number, upper=True)

    try:
        cut = cut_aliases[cached_clean_upper(cut)]
    except KeyError as e:
        raise KeyValueError('cut_aliases', e.args[0])

    carat_weight = Decimal(str(cached_clean(carat_weight)))
    if carat_weight < minimum_carat_weight:
        raise SkipDiamond("Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight))
    elif maximum_carat_weight and carat_weight > maximum_carat_weight:
        raise SkipDiamond("Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight))

    color = color_aliases.get(cached_clean_upper(color))

    certifier = cached_clean_upper(certifier)
    # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
    if must_be_certified:
        if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
            raise SkipDiamond('No valid Certifier was specified.')
    try:
        certifier_id, certifier_disabled = certifier_aliases[certifier]
    except KeyError as e:
        raise KeyValueError('certifier_aliases', e.args[0])

    if certifier_disabled:
        raise SkipDiamond('Certifier disabled')

    if certifier and not certifier_id:
        new_certifier = models.Certifier.objects.create(name=certifier, abbr=certifier)
        certifier_aliases.update({certifier: (int(new_certifier.id), new_certifier.disabled)})
        certifier = new_certifier.pk
    else:
        certifier = certifier_id

    clarity = cached_clean_upper(clarity)
    if not clarity:
        raise SkipDiamond('No clarity specified')
    try:
        clarity = clarity_aliases[clarity]
    except KeyError as e:
        raise KeyValueError('clarity', e.args[0])

    cut_grade = grading_aliases.get(cached_clean_upper(cut_grade))
    carat_price = clean(carat_price.replace(',', ''))
    try:
        carat_price = Decimal(carat_price)
    except InvalidOperation:
        carat_price = None

    try:
        depth_percent = Decimal(str(clean(depth_percent)))
    except InvalidOperation:
        depth_percent = 'NULL'

    try:
        table_percent = Decimal(str(cached_clean(table_percent)))
    except InvalidOperation:
        table_percent = 'NULL'

    girdle = cached_clean_upper(girdle)
    if not girdle or girdle == '-':
        girdle = ''

    culet = cached_clean_upper(culet)
    polish = grading_aliases.get(cached_clean_upper(polish))
    symmetry = grading_aliases.get(cached_clean_upper(symmetry))

    fluorescence = cached_clean_upper(fluorescence)
    fluorescence_id = None
    fluorescence_color = None
    fluorescence_color_id = None
    for abbr, id in fluorescence_aliases.iteritems():
        if fluorescence.startswith(abbr.upper()):
            fluorescence_id = id
            fluorescence_color = fluorescence.replace(abbr.upper(), '')
            continue
    fluorescence = fluorescence_id

    if fluorescence_color:
        fluorescence_color = cached_clean_upper(fluorescence_color)
        for abbr, id in fluorescence_color_aliases.iteritems():
            if fluorescence_color.startswith(abbr.upper()):
                fluorescence_color_id = id
                continue
        if not fluorescence_color_id: fluorescence_color_id = None
    fluorescence_color = fluorescence_color_id

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

    if length == '0':
        length = None
    if width == '0':
        width = None
    if depth == '0':
        depth = None

    """
    if manmade == '1':
        manmade = 't'
    else:
        manmade = 'f'
    """

    if carat_price is None:
        raise SkipDiamond('No carat_price specified')

    # Initialize price after all other data has been initialized
    price_before_markup = carat_price * carat_weight

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

    # Order must match struture of tsj_gemstone_diamond table
    ret = Row(
        added_date,
        added_date,
        't', # active
        SOURCE_NAME,
        '', # lot_num
        stock_number,
        owner,
        cut,
        nvl(cut_grade),
        nvl(color),
        clarity,
        carat_weight,
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
        nvl(polish),
        nvl(symmetry),
        nvl(fluorescence_id),
        nvl(fluorescence_color_id),
        nvl(length),
        nvl(width),
        nvl(depth),
        comment,
        city,
        state,
        country,
        'NULL', # rap_date
        'NULL', # manmade
    )

    return ret