from collections import defaultdict, namedtuple
from datetime import datetime
from decimal import Decimal
import csv
import logging
import tempfile
import xml.sax

from django.conf import settings
from django.db import connection, transaction

from .. import models
from ..prefs import prefs

logger = logging.getLogger('tsj_gemstone.backends')
summary_logger = logging.getLogger('tsj_gemstone.backends.summary')

class KeyValueError(Exception):
    def __init__(self, key, value):
        self.key, self.value = key, value

    def __str__(self):
        return 'KeyValueError: %s[%s]' % (self.key, self.value)

class SkipDiamond(Exception):
    pass

class SkipImport(Exception):
    pass

class BaseBackend(object):
    filename = None

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
        'rap_date'
    ))

    def __init__(self, filename=None, nodebug=False):
        self.filename = filename
        self.backend_module = self.__module__.split('.')[-1]
        self.nodebug = nodebug

        self.missing_values = defaultdict(set)
        self.import_successes = 0
        self.import_errors = 0
        self.import_skip = 0

    @property
    def enabled(self):
        try:
            return prefs.get(self.backend_module)
        except KeyError:
            return False

    def get_default_filename(self):
        return self.default_filename

    def get_fp(self):
        fn = ''
        if self.filename:
            fn = self.filename

        elif settings.DEBUG and not self.nodebug:
            fn = self.debug_filename

        else:
            fn = self.get_default_filename()

        if fn:
            try:
                return open(fn, 'rU')
            except IOError:
                logger.exception(
                    'Error loading file',
                    extra={
                        'tags': {
                            'backend': self.backend_module,
                        },
                    },
                )
        else:
            raise SkipImport

    def populate_import_data(self):
        # We want all the imported records to have the same added_date
        self.added_date = datetime.now()

        self.cut_aliases = models.Cut.objects.as_dict()
        self.color_aliases = models.Color.objects.as_dict()
        self.clarity_aliases = models.Clarity.objects.as_dict()
        self.grading_aliases = models.Grading.objects.as_dict()
        self.fluorescence_aliases = models.Fluorescence.objects.as_dict()
        self.fluorescence_color_aliases = models.FluorescenceColor.objects.as_dict()
        self.certifier_aliases = models.Certifier.objects.as_dict_disabled()

        self.markup_list = models.DiamondMarkup.objects.values_list('start_price', 'end_price', 'percent')

        self.pref_values = (
            Decimal(prefs.get('rapaport_minimum_carat_weight', '0.2')),
            Decimal(prefs.get('rapaport_maximum_carat_weight', '5')),
            Decimal(prefs.get('rapaport_minimum_price', '1500')),
            Decimal(prefs.get('rapaport_maximum_price', '200000')),
            prefs.get('rapaport_must_be_certified', True),
            prefs.get('rapaport_verify_cert_images', False),
        )

    def save(self, fp):
        # fp should be a tempfile.NamedTemporaryFile.  We currently assume
        # that it's also still open in write mode, so flush and reopen.
        fp.flush()
        fp = open(fp.name)

        with transaction.atomic():
            # FIXME: Don't truncate/replace the table if the import returned no data
            try:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM tsj_gemstone_diamond WHERE source='%s'" % self.backend_module)
                cursor.copy_from(fp, 'tsj_gemstone_diamond', null='NULL', columns=self.Row._fields)
            except Exception as e:
                logger.exception("Error on copy_from for %s" % self.backend_module)

        fp.close()

        if self.missing_values:
            for k, v in self.missing_values.items():
                self.import_errors += 1
                self.report_missing_values(k, v)

        if self.import_skip:
            self.report_skipped_diamonds(self.import_skip)

        return self.import_successes, self.import_errors

    def report_missing_values(self, field, values):
        summary_logger.warning(
            'Missing values for %s' % field,
            extra={
                'tags': {
                    'backend': self.backend_module,
                },
                'summary_detail': ', '.join(sorted(values)),
            },
        )

    def report_skipped_diamonds(self, count):
        summary_logger.warning(
            'Skipped diamonds',
            extra={
                'tags': {
                    'backend': self.backend_module,
                },
                'summary_detail': count,
            },
        )

    def nvl(self, data):
        if data is None or data == '':
            return 'NULL'
        return data

class CSVBackend(BaseBackend):
    def run(self):
        # TODO: Shouldn't have to call this explicitly in each backend
        self.populate_import_data()

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
        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        # To cut down on disk writes, we buffer the rows
        row_buffer = []
        buffer_size = 1000

        for line in reader:
            # Sometimes the feed has blank lines
            if not line:
                continue

            # Rather than fail on malformed CSVs, pad rows which have fewer
            # columns than the header row
            col_diff = (len(headers) - blank_columns) - len(line)
            if col_diff > 0:
                line.extend([''] * col_diff)

            # And sometimes there's one too many columns between J (cert #) and M (dimensions)
            # TODO: Commented out since they seem to have resolved this issue

            # TODO: We shouldn't need KeyError or ValueError if we're correctly
            #       accounting for the possible failure conditions with SkipDiamond
            #       and KeyValueError.
            try:
                diamond_row = self.write_diamond_row(line, blank_columns=blank_columns)
            except SkipDiamond as e:
                self.import_skip += 1
                print e.message
                #logger.info('SkipDiamond: %s' % e.message)
                continue
            except KeyValueError as e:
                print e
                self.missing_values[e.key].add(e.value)
            except KeyError as e:
                self.import_errors += 1
                logger.info('KeyError', exc_info=e)
            except ValueError as e:
                print e
                self.import_errors += 1
                logger.info('ValueError', exc_info=e)
            except Exception as e:
                print e
                # Create an error log entry and increment the import_errors counter
                #import_error_log_details = str(line) + '\n\nTOTAL FIELDS: ' + str(len(line)) + '\n\nTRACEBACK:\n' + traceback.format_exc()
                #if import_log: ImportLogEntry.objects.create(import_log=import_log, csv_line=reader.line_num, problem=str(e), details=import_error_log_details)
                self.import_errors += 1
                logger.error('Diamond import exception', exc_info=e)
            else:
                if len(row_buffer) > buffer_size:
                    writer.writerows(row_buffer)
                    row_buffer = [diamond_row]
                else:
                    row_buffer.append(diamond_row)
                self.import_successes += 1

        if row_buffer:
            writer.writerows(row_buffer)

        return self.save(tmp_file)

class JSONBackend(BaseBackend):
    def run(self):
        self.populate_import_data()

        data = self.get_json()
        if not data:
            return 0, 1

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        # To cut down on disk writes, we buffer the rows
        row_buffer = []
        buffer_size = 1000

        # TODO: We shouldn't need KeyError or ValueError if we're correctly
        #       accounting for the possible failure conditions with SkipDiamond
        #       and KeyValueError.
        missing_values = defaultdict(set)

        for line in data:
            try:
                diamond_row = self.write_diamond_row(line)
            except SkipDiamond as e:
                print e
                self.import_skip += 1
                #logger.info('SkipDiamond: %s' % e.message)
                continue
            except KeyValueError as e:
                print e
                self.missing_values[e.key].add(e.value)
            except KeyError as e:
                print e
                self.import_errors += 1
                logger.info('KeyError', exc_info=e)
            except ValueError as e:
                print e
                self.import_errors += 1
                logger.info('ValueError', exc_info=e)
            except Exception as e:
                print e
                # Create an error log entry and increment the import_errors counter
                #import_error_log_details = str(line) + '\n\nTOTAL FIELDS: ' + str(len(line)) + '\n\nTRACEBACK:\n' + traceback.format_exc()
                #if import_log: ImportLogEntry.objects.create(import_log=import_log, csv_line=reader.line_num, problem=str(e), details=import_error_log_details)
                self.import_errors += 1
                logger.error('Diamond import exception', exc_info=e)
                break
            else:
                if len(row_buffer) > buffer_size:
                    writer.writerows(row_buffer)
                    row_buffer = [diamond_row]
                else:
                    row_buffer.append(diamond_row)
                self.import_successes += 1

        if row_buffer:
            writer.writerows(row_buffer)

        return self.save(tmp_file)

class XMLHandler(xml.sax.ContentHandler):
    def __init__(self, backend, writer):
        # ContentHandler is an old-style class
        xml.sax.ContentHandler.__init__(self)

        self.backend, self.writer = backend, writer

        # To cut down on disk writes, we buffer the rows
        self.row_buffer = []
        self.buffer_size = 1000

class XMLBackend(BaseBackend):
    # An XML backend requires a subclass of XMLHandler to process the document
    #handler_class = XMLHandler

    def get_handler(self, writer):
        return self.handler_class(self, writer)

    def run(self):
        # TODO: Shouldn't have to call this explicitly in each backend
        self.populate_import_data()

        fp = self.get_fp()
        if not fp:
            return 0, 1

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        XmlParser = xml.sax.make_parser()
        XmlParser.setContentHandler(self.get_handler(writer))
        XmlParser.parse(fp)

        return self.save(tmp_file)
