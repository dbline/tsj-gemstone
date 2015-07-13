from collections import defaultdict, namedtuple
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import logging
import os
import re
from string import ascii_letters, digits, whitespace, punctuation
import tempfile
import time

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

SOURCE_NAME = 'stuller'

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

def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('x')
        if float(length) > 100 or float(width) > 100 or float(depth) > 100:
            raise ValueError
    except ValueError:
        length, width, depth = None, None, None

    return length, width, depth

class Backend(BaseBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/stuller.json')

    def get_json(self):
        if self.filename:
            return json.load(open(self.filename, 'rb'))['Diamonds']

        # TODO: We should put a couple paginated JSON files in ../tests/data
        #       so that we can run through the loop below when debugging
        if settings.DEBUG and not self.nodebug:
            return json.load(open(self.debug_filename, 'rb'))['Diamonds']

        user = settings.STULLER_USER
        pw = settings.STULLER_PASSWORD

        session = requests.Session()
        session.auth = (user, pw)
        session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})
        url = 'https://www.stuller.com/api/v2/gem/diamonds'
        next_page = None
        ret = []

        # Accumulate paginated diamond data into ret
        while True:
            if next_page:
                # Stuller wants a JSON request body, not urlencoded form data
                response = session.post(url, data=json.dumps({'NextPage': next_page}))
            else:
                response = session.get(url)

            if response.status_code != 200:
                logger.error('Stuller HTTP error {}'.format(response.status_code))
                return

            data = response.json()
            if 'Diamonds' not in data:
                break

            ret.extend(data['Diamonds'])

            if 'NextPage' in data and data['NextPage']:
                next_page = data['NextPage']
                time.sleep(3)
            else:
                break

        return ret

    def run(self):
        data = self.get_json()
        if not data:
            return 0, 1

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % SOURCE_NAME)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        import_successes = 0
        import_errors = 0

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

        for line in data:
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
                    pref_values
                )
            except SkipDiamond as e:
                #logger.info('SkipDiamond: %s' % e.message)
                continue
                # TODO: Increment import_errors?
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

        return import_successes, import_errors

# TODO: Move somewhere more general
def nvl(data):
    if data is None:
        return 'NULL'
    return data

def write_diamond_row(data, cut_aliases, color_aliases, clarity_aliases, grading_aliases, fluorescence_aliases, fluorescence_color_aliases, certifier_aliases, markup_list, added_date, pref_values):

    minimum_carat_weight, maximum_carat_weight, minimum_price, maximum_price, must_be_certified, verify_cert_images = pref_values

    stock_number = clean(str(data.get('SerialNumber')))
    comment = cached_clean(data.get('Comments'))
    try:
        cut = cut_aliases[cached_clean_upper(data.get('Shape'))]
    except KeyError as e:
        raise KeyValueError('cut_aliases', e.args[0])

    carat_weight = Decimal(cached_clean(str(data.get('CaratWeight'))))
    if carat_weight < minimum_carat_weight:
        raise SkipDiamond("Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight))
    elif maximum_carat_weight and carat_weight > maximum_carat_weight:
        raise SkipDiamond("Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight))

    color = color_aliases.get(cached_clean_upper(data.get('Color')))

    certifier = cached_clean_upper(data.get('Certification'))
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

    clarity = cached_clean_upper(data.get('Clarity'))
    if not clarity:
        raise SkipDiamond('No clarity specified')
    try:
        clarity = clarity_aliases[clarity]
    except KeyError as e:
        raise KeyValueError('clarity', e.args[0])

    cut_grade = grading_aliases.get(cached_clean_upper(data.get('Make')))
    try:
        if isinstance(data.get('PricePerCarat'), dict):
            # TODO: Verify that data['PricePerCarat']['CurrencyCode'] is USD
            carat_price = clean(str(data['PricePerCarat'].get('Value')))
            if carat_price:
                carat_price = Decimal(carat_price)
            else:
                carat_price = None
        else:
            carat_price = None
    except AttributeError:
        raise
        carat_price = None

    try:
        depth_percent = Decimal(clean(str(data.get('Depth'))))
        if depth_percent > 100:
            raise InvalidOperation
    except InvalidOperation:
        depth_percent = 'NULL'

    try:
        table_percent = Decimal(cached_clean(str(data.get('Table'))))
        if table_percent > 100:
            raise InvalidOperation
    except InvalidOperation:
        table_percent = 'NULL'

    if data.get('Girdle'):
        girdle_thinnest = cached_clean_upper(data['Girdle'])
        girdle = [girdle_thinnest]
        if data.get('Girdle2'):
            girdle_thickest = cached_clean_upper(data['Girdle2'])
            girdle.append(girdle_thickest)
        girdle = ' - '.join(girdle)
    else:
        girdle = ''

    culet = cached_clean_upper(data.get('Culet'))
    polish = grading_aliases.get(cached_clean_upper(data.get('Polish')))
    symmetry = grading_aliases.get(cached_clean_upper(data.get('Symmetry')))

    # Fluorescence and color are combined, e.g 'FAINT BLUE'
    fl = data.get('Fluorescence', '')
    if ' ' in fl:
        fl, flcolor = fl.split(' ')
        fluorescence = cached_clean_upper(fl)
        fluorescence_color = cached_clean_upper(flcolor)

        for abbr, id in fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                continue
        fluorescence = fluorescence_id

        for abbr, id in fluorescence_color_aliases.iteritems():
            if fluorescence_color.startswith(abbr.upper()):
                fluorescence_color_id = id
                continue
        if fluorescence_color_id:
            fluorescence_color = fluorescence_color_id
        else:
            fluorescence_color_id = None
    else:
        fluorescence_id = None
        fluorescence_color_id = None

    measurements = clean(data.get('Measurements'))
    length, width, depth = split_measurements(measurements)

    cert_num = clean(data.get('CertificationNumber'))
    if not cert_num:
        cert_num = ''

    cert_image = data.get('CertificatePath')
    if not cert_image:
        cert_image = ''
    elif verify_cert_images and cert_image != '' and not url_exists(cert_image):
        cert_image = ''

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

    state = cached_clean(data.get('st'))
    country = cached_clean(data.get('cty'))

    # TODO: Matching pair stock number is data['psr']

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
        certifier,
        cert_num,
        cert_image,
        '', # cert_image_local
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
        '', # city,
        state,
        country,
        'NULL' # rap_date
    )

    return ret
