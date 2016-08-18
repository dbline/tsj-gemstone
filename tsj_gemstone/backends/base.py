from collections import defaultdict, namedtuple
from datetime import datetime
from decimal import Decimal
import csv
import logging
import tempfile
import xml.sax

from psycopg2.extras import Json

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

# A failure to load source data from the backend (HTTP error, API error, missing file, etc)
class ImportSourceError(Exception):
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

    def __init__(self, filename=None, nodebug=False, task_id=None):
        self.filename = filename
        self.backend_module = self.__module__.split('.')[-1]
        self.nodebug = nodebug
        self.task_id = task_id

        # PK of tsj_gemstone_central_import record that corresponds to the
        # currently running import
        self.import_id = None

        # Outer keys are field names (cut, clarity, certifier, ..)
        # Inner keys are the value (Round, Foggy, Bob's Lab, ..)
        self.missing_values = defaultdict(lambda: defaultdict(int))

        self.import_successes = 0

        # Keys are the exception message
        self.import_skip = defaultdict(int)
        self.import_errors = defaultdict(int)

        # To cut down on disk writes, we buffer the rows
        self.row_buffer = []
        self.buffer_size = 1000

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
            except IOError as e:
                raise ImportSourceError(str(e))
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

    def create_import_record(self):
        "Add a record to tsj_gemstone_central_import to track import status"
        cursor = connection.cursor()
        if self.task_id:
            cursor.execute('SELECT create_gemstone_import(%s,%s)', (self.backend_module, self.task_id))
        else:
            cursor.execute('SELECT create_gemstone_import(%s)', (self.backend_module,))
        self.import_id = cursor.fetchone()[0]

    def update_import_record(self, status):
        cursor = connection.cursor()

        if status in ('processed', 'error'):
            data = {}
            for k in ('import_successes', 'missing_values', 'import_errors', 'import_skip'):
                if getattr(self, k):
                    if k.startswith('import_'):
                        dk = k[7:]
                    elif k == 'missing_values':
                        dk = 'missing'
                    data[dk] = getattr(self, k)
            cursor.execute(
                'SELECT update_gemstone_import(%s,%s,%s)',
                (self.import_id, status, Json(data))
            )
        # TODO: update states:
        #  - Loading from source
        #  - write_diamond_row'ing
        #  - copy_from'ing

    def run(self):
        self.create_import_record()
        self.populate_import_data()

        try:
            tmp_file = self._run()
            self.save(tmp_file)
        except ImportSourceError as e:
            # TODO: Bit of a hack.  We should represent backend-level errors
            #       differently from record-level errors.
            self.import_errors[str(e)] = 1
            self.update_import_record('error')
            return

        self.update_import_record('processed')

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

    def try_write_row(self, writer, *args, **kwargs):
        # TODO: We shouldn't need KeyError or ValueError if we're correctly
        #       accounting for the possible failure conditions with SkipDiamond
        #       and KeyValueError.
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
            if len(self.row_buffer) > self.buffer_size:
                writer.writerows(self.row_buffer)
                self.row_buffer = [diamond_row]
            else:
                self.row_buffer.append(diamond_row)
            self.import_successes += 1

    def nvl(self, data):
        if data is None or data == '':
            return 'NULL'
        return data

class CSVBackend(BaseBackend):
    def _run(self):
        fp = self.get_fp()
        reader = csv.reader(fp)

        try:
            headers = reader.next()
        except StopIteration as e:
            raise ImportSourceError('Unable to read headers')

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

                self.try_write_row(writer, line, blank_columns=blank_columns)
        except csv.Error as e:
            raise ImportSourceError(str(e))

        if self.row_buffer:
            writer.writerows(self.row_buffer)

        return tmp_file

class JSONBackend(BaseBackend):
    def _run(self):
        data = self.get_json()

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        for obj in data:
            self.try_write_row(writer, obj)

        if self.row_buffer:
            writer.writerows(self.row_buffer)

        return tmp_file

class XMLHandler(xml.sax.ContentHandler):
    def __init__(self, backend, writer):
        # ContentHandler is an old-style class
        xml.sax.ContentHandler.__init__(self)

        self.backend, self.writer = backend, writer

class XMLBackend(BaseBackend):
    # An XML backend requires a subclass of XMLHandler to process the document
    #handler_class = XMLHandler

    def get_handler(self, writer):
        return self.handler_class(self, writer)

    def _run(self):
        fp = self.get_fp()

        tmp_file = tempfile.NamedTemporaryFile(mode='w', prefix='gemstone_diamond_%s.' % self.backend_module)
        writer = csv.writer(tmp_file, quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n', delimiter='\t')

        XmlParser = xml.sax.make_parser()
        XmlParser.setContentHandler(self.get_handler(writer))
        XmlParser.parse(fp)

        return tmp_file
