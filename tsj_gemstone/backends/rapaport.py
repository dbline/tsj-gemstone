import csv
from datetime import datetime
from decimal import Decimal
import logging
import os
from string import ascii_letters, digits, whitespace, punctuation
from time import strptime
import tempfile
import urllib
from urllib2 import Request, urlopen, URLError, HTTPError

from django.conf import settings
from django.db import connection, transaction

from .. import models
from ..prefs import prefs
from ..utils import moneyfmt

logger = logging.getLogger(__name__)

VALID_CHAR_LIST = (ascii_letters + digits + whitespace + punctuation)
def clean(var, newlines=True, upper=False):
    # TODO: Replace with regex?
    var = ''.join([ch for ch in var if ch in VALID_CHAR_LIST])
    var = var.replace('\\', '').strip()

    if newlines:
        var = var.replace('\n', '').replace('\r', '')
    if upper:
        var = var.upper()

    return var

def split_measurements(measurements):
    try:
        length, width, depth = measurements.split('x')
    except ValueError:
        try:
            length, width, depth = measurements.split('*')
        except:
            length, width, depth = 'NULL', 'NULL', 'NULL'

    return {
        'length': length or 'NULL',
        'width': width or 'NULL',
        'depth': depth or 'NULL'
    }

def main():
    if not settings.DEBUG:
        username = prefs.get('rapaport_username')
        password = prefs.get('rapaport_password')

        if not username or not password:
            logger.warning('Missing rapaport credentials, aborting import.')
            return 0, 1

        # The URLs to authenticate with and download from
        auth_url = 'https://technet.rapaport.com/HTTP/Authenticate.aspx'
        url = 'http://technet.rapaport.com/HTTP/RapLink/download.aspx'

        # Post the username and password to the auth_url and save the resulting ticket
        auth_data = urllib.urlencode({
            'username': username,
            'password': password})
        auth_request = Request(auth_url, auth_data)
        try:
            ticket = urlopen(auth_request).read()
        except HTTPError as e:
            logger.error('Rapaport auth failure: %s' % e)
            return 0, 1

        # Download the CSV
        feed_data = urllib.urlencode({'SortBy': 'Owner', 'White': '1', 'Programmatically': 'yes', 'Version': '0.8', 'ticket': ticket})
        rap_list_request = Request(url + '?' + feed_data)
        rap_list = urlopen(rap_list_request)

        # Load the CSV file into the CSV reader for parsing
        reader = csv.reader(rap_list)
    else:
        # This is for development only. Load a much smaller version of the diamonds database from the fixtures directory.
        reader = csv.reader(open(os.path.join(os.path.dirname(__file__), '../tests/data/rapnet-v0.8-225rows.csv'), 'rb'))

    # Skip the first line because it contains row names that we don't care about
    reader.next()

    # Prepare a temp file to use for writing our output CSV to
    tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond.')
    #writer = csv.writer(tmp_file, quoting=csv.QUOTE_MINIMAL, doublequote=True, escapechar='\\', lineterminator='\n')
    writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')
    
    # Prepare some needed variables
    import_successes = 0
    import_errors = 0
    
    # Create the import log now so we can add entries to it and update it with successes and failures after we're done
    #import_log = models.ImportLog.objects.create(type='D')

    # Setup the abbreviation and alias matching dictionaries
    cut_aliases = models.Cut.objects.as_dict()
    color_aliases = models.Color.objects.as_dict()
    clarity_aliases = models.Clarity.objects.as_dict()
    grading_aliases = models.Grading.objects.as_dict()
    fluorescence_aliases = models.Fluorescence.objects.as_dict()
    fluorescence_color_aliases = models.FluorescenceColor.objects.as_dict()
    certifier_aliases = models.Certifier.objects.as_dict_disabled()

    # Prepare the markup list so that we don't have to make a DB query each time
    markup_list = []
    markups = models.DiamondMarkup.objects.all()
    for markup in markups:
        markup_list.append((markup.start_price, markup.end_price, markup.percent))

    # Loop through each line in the reader
    for line in reader:
        try:
            diamond_row = write_diamond_row(line, cut_aliases, color_aliases, clarity_aliases, grading_aliases, fluorescence_aliases, fluorescence_color_aliases, certifier_aliases, markup_list)
        except KeyError, e:
            import_errors += 1
            logger.info('KeyError', exc_info=e)
        except ValueError, e:
            import_errors += 1
            logger.info('ValueError', exc_info=e)
        except Exception, e:
            # Create an error log entry and increment the import_errors counter
            #import_error_log_details = str(line) + '\n\nTOTAL FIELDS: ' + str(len(line)) + '\n\nTRACEBACK:\n' + traceback.format_exc()
            #if import_log: ImportLogEntry.objects.create(import_log=import_log, csv_line=reader.line_num, problem=str(e), details=import_error_log_details)
            import_errors += 1
            logger.error('Diamond import exception', exc_info=e)
        else:
            writer.writerow(diamond_row)
            import_successes += 1

    #import_log.successes = import_successes
    #import_log.failures = import_errors
    #import_log.save()

    tmp_file.flush()
    tmp_file = open(tmp_file.name)

    @transaction.commit_manually
    def copy_from():
        # FIXME: Don't truncate/replace the table if the import returned no data
        try:
            cursor = connection.cursor()
            cursor.execute('TRUNCATE TABLE tsj_gemstone_diamond CASCADE')
            cursor.copy_from(tmp_file, 'tsj_gemstone_diamond', null='NULL')
        except Exception as e:
            transaction.rollback()
            raise
        else:
            transaction.commit()

    copy_from()
    tmp_file.close()

    return import_successes, import_errors

def write_diamond_row(line, cut_aliases, color_aliases, clarity_aliases, grading_aliases, fluorescence_aliases, fluorescence_color_aliases, certifier_aliases, markup_list):
    lot_num, owner, cut, carat_weight, color, clarity, cut_grade, carat_price, rap_percent, certifier, depth_percent, table_percent, girdle, culet, polish, symmetry, fluorescence, measurements, comment, num_stones, cert_num, stock_number, make, rap_date, city, state, country, cert_image = line

    # Setup the diamond import requirements
    minimum_carat_weight = Decimal(prefs.get('rapaport_minimum_carat_weight', '0.2'))
    maximum_carat_weight = Decimal(prefs.get('rapaport_maximum_carat_weight', '5'))
    minimum_price = Decimal(prefs.get('rapaport_minimum_price', '1500'))
    maximum_price = Decimal(prefs.get('rapaport_maximum_price', '200000'))
    must_be_certified = prefs.get('rapaport_must_be_certified', True)
    verify_cert_images = prefs.get('rapaport_verify_cert_images', False)

    added_date = datetime.now()
    lot_num = clean(lot_num)
    owner = clean(owner).title()
    comment = clean(comment)
    stock_number = clean(stock_number, upper=True)
    rap_date = datetime(*strptime(clean(rap_date), '%m/%d/%Y %I:%M:%S %p')[0:6])
    city = clean(city)
    state = clean(state)
    country = clean(country)

    cut = cut_aliases[clean(cut, upper=True)]

    carat_weight = Decimal(str(clean(carat_weight)))
    if carat_weight < minimum_carat_weight:
        raise ValueError, "Carat Weight '%s' is less than the minimum of %s." % (carat_weight, minimum_carat_weight)
    elif maximum_carat_weight and carat_weight > maximum_carat_weight:
        raise ValueError, "Carat Weight '%s' is greater than the maximum of %s." % (carat_weight, maximum_carat_weight)

    color = color_aliases[clean(color, upper=True)]

    certifier = clean(certifier, upper=True)
    # If the diamond must be certified and it isn't, raise an exception to prevent it from being imported
    if must_be_certified:
        if not certifier or certifier.find('NONE') >= 0 or certifier == 'N':
            raise ValueError, "No valid Certifier was specified."
    certifier_id, certifier_disabled = certifier_aliases.get(certifier)

    if certifier_disabled:
        raise ValueError, "Certifier disabled"

    if certifier and not certifier_id:
        new_certifier = models.Certifier.objects.create(name=certifier, abbr=certifier)
        certifier_aliases.update({certifier: (int(new_certifier.id), new_certifier.disabled)})
        certifier = new_certifier.pk
    else:
        certifier = certifier_id

    clarity = clarity_aliases[clean(clarity, upper=True)]

    cut_grade = grading_aliases.get(clean(cut_grade, upper=True))
    if not cut_grade:
        cut_grade = 'NULL'

    carat_price = Decimal(str(clean(carat_price)))

    try:
        depth_percent = Decimal(str(clean(depth_percent)))
    except:
        depth_percent = 'NULL'

    try:
        table_percent = Decimal(str(clean(table_percent)))
    except:
        table_percent = 'NULL'

    girdle = clean(girdle, upper=True)
    if not girdle or girdle == '-':
        girdle = ''

    culet = clean(culet, upper=True)
    if culet == 'NULL':
        culet = ''

    polish = grading_aliases.get(clean(polish, upper=True))
    if not polish:
        polish = 'NULL'

    symmetry = grading_aliases.get(clean(symmetry, upper=True))
    if not symmetry:
        symmetry = 'NULL'

    fluorescence = clean(fluorescence, upper=True)
    fluorescence_id = None
    fluorescence_color = None
    for abbr, id in fluorescence_aliases.iteritems():
        if fluorescence.startswith(abbr.upper()):
            fluorescence_id = id
            fluorescence_color = fluorescence.replace(abbr.upper(), '')
            continue
    if not fluorescence_id: fluorescence_id = 'NULL'
    fluorescence = fluorescence_id

    fluorescence_color_id = 'NULL'
    if fluorescence_color:
        fluorescence_color = clean(fluorescence_color, upper=True)
        for abbr, id in fluorescence_color_aliases.iteritems():
            if fluorescence_color.startswith(abbr.upper()):
                fluorescence_color_id = id
                continue
        if not fluorescence_color_id: fluorescence_color_id = 'NULL'
    fluorescence_color = fluorescence_color_id

    measurements = clean(measurements)
    measurements_dict = split_measurements(measurements)
    length = measurements_dict['length']
    width = measurements_dict['width']
    depth = measurements_dict['depth']
    measurements = measurements

    cert_num = clean(cert_num)
    if not cert_num:
        cert_num = ''

    cert_image = cert_image.replace('.net//', '.net/').replace('\\', '/').strip()
    if not cert_image:
        cert_image = ''
    elif verify_cert_images and cert_image != '' and not url_exists(cert_image):
        cert_image = ''

    # Initialize these after all other data has been initialized
    price_before_markup = carat_price * carat_weight

    if minimum_price and price_before_markup < minimum_price:
        raise ValueError, "Price before markup '%s' is less than the minimum of %s." % (price_before_markup, minimum_price)
    if maximum_price and price_before_markup > maximum_price:
        raise ValueError, "Price before markup '%s' is greater than the maximum of %s." % (price_before_markup, maximum_price)

    price = None
    for markup in markup_list:
        if markup[0] <= price_before_markup and markup[1] >= price_before_markup:
            price = (price_before_markup * (1 + markup[2]/100))
            break
    if not price:
        raise KeyError, "A diamond markup doesn't exist for a diamond with pre-markup price of '%s'." % price_before_markup

    ret = (
        added_date,
        added_date,
        lot_num,
        stock_number,
        owner,
        cut,
        cut_grade,
        color,
        clarity,
        carat_weight,
        moneyfmt(Decimal(carat_price), curr='', sep=''),
        moneyfmt(Decimal(price), curr='', sep=''),
        certifier,
        cert_num,
        cert_image,
        depth_percent,
        table_percent,
        girdle,
        culet,
        polish,
        symmetry,
        fluorescence,
        fluorescence_color,
        length,
        width,
        depth,
        comment,
        city,
        state,
        country,
        rap_date
    )

    return ret
