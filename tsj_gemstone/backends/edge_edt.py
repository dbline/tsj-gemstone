from decimal import Decimal, InvalidOperation
import glob
import json
import logging
import tempfile
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
from operator import add

from .base import LRU_CACHE_MAXSIZE, JSONBackend, SkipDiamond, KeyValueError, ImportSourceError
from .. import models
from ..utils import moneyfmt
from tsj_pointofsale.prefs import prefs as pos_prefs
from tsj_gemstone.prefs import prefs

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

class Backend(JSONBackend):
    debug_filename = os.path.join(os.path.dirname(__file__), '../tests/data/edt_sample_file.json')
    DEFAULT_SOURCE = 'tsj-pointofsale-edge-edt'

    def __init__(self, *args, **kwargs):
        super(Backend, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.partial_import = pos_prefs.get('partial_import', True)
        self.ftp_name = pos_prefs.get('ftp_username', '')
        self.gemstone_category = 195

    def digits_check(self, s, length=5):
        if sum(c.isdigit() for c in str(s)) > length:
            self.logger.info('Skipping Diamond "%s" - numeric value out of range' % stock_number)
            raise SkipDiamond('numeric value out of allowed range')
        return

    def file_patterns(self, directory):

        if self.partial_import:
            patterns = ['*-ItemList.json']
        else:
            patterns = ['*-FullItemList.json']
        return map(lambda p:os.path.join(directory, p), patterns)

    def get_reader(self, **kwargs):
        if not hasattr(self, '_reader'):

            #inventory_filename = '2021-03-22-13-27-19-FullItemList.json'
            inventory_filename = kwargs.get('inventory_filename')
            if not inventory_filename:
                fn = self.get_default_filename()
                if not fn or not os.path.exists(fn):
                    raise Exception('No file found')
                inventory_filename = fn
            if not hasattr(self, '_rawdata'):
                self.logger.info('Opening %s' % inventory_filename)
                self._rawdata = json.load(open(inventory_filename))

            if 'Items' not in self._rawdata:
                raise Exception('File is does not contain EDT items.')

            def edt_item_iter(data):
                for item in data['Items']:
                    if 'PairValue' not in item:
                         continue
                    if 'ItemCatId' in item['PairValue'] and item['PairValue']['ItemCatId'] != self.gemstone_category:
                        continue
                    i = dict((k,v) for k,v in filter(lambda x:not isinstance(x[1], (list, dict)), item['PairValue'].items()))
                    if 'Stones' in item['PairValue'] and item['PairValue']['Stones']:
                        for index, stone in enumerate(item['PairValue']['Stones']):
                            values = dict(map(lambda s:('stone_%d_%s' % (index, s[0]), s[1]), stone.get('PairValue', {}).items()))
                            i.update(values)
                    yield i

            self._reader = edt_item_iter(self._rawdata)
        return self._reader

    @property
    def enabled(self):
        try:
            return self.backend_module in prefs.get('backend')
        except TypeError:
            return False

    @classmethod
    def latest_file_from_patterns(cls, patterns):
        # FIXME: list all files only once (currently listing through everything twice).
        file_list = reduce(add, map(lambda p: list(glob.iglob(p)), patterns), list())
        if not file_list:
            return None
        return max(file_list, key=os.path.getmtime)

    def get_default_filename(self):
        if not self.ftp_name:
            raise Exception('ftp name not set')
        _maybe_dir = filter(os.path.isdir, glob.glob(os.path.join(settings.FTP_ROOT, self.ftp_name, '*', 'Inbox')))
        if not len(_maybe_dir):
            raise IOError('Required Inbox directory not found.')
        infile_glob = self.file_patterns(_maybe_dir[0])

        fn= self.latest_file_from_patterns(infile_glob)
        if fn:
            self.logger.info('Importing {schema} EDGE-EDT Diamonds from file "%s"' % fn)
            return fn


    def file_patterns(self, directory):

        if self.partial_import:
            patterns = ['*-ItemList.json']
        else:
            patterns = ['*-FullItemList.json']
        return map(lambda p: os.path.join(directory, p), patterns)

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
                diamond.data = json.loads(diamond_row.data)
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

    def write_diamond_row(self, item):

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

        stock_number = clean(item['ItemKey'], upper=True)
        lot_num = clean(item['stone_0_StoneSeq'], upper=True)

        if item['ItemStatus'] == 'I':
            status = 't'
        else:
            status = 'f'

        #if item['ItemCatId'] != '195':
        #   raise SkipDiamond('Not a diamond')

        try:
            cut = self.cut_aliases[cached_clean(item['stone_0_StoneShape'], upper=True)]
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Cut Aliases' % stock_number)
            raise KeyValueError('cut_aliases', e.args[0],)


        try:
            carat_weight = item['stone_0_StoneTWT']
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Carat Weight' % stock_number)
            raise KeyValueError('carat_weight', e.args[0])
        if carat_weight < minimum_carat_weight:
            raise SkipDiamond('Carat weight is less than the minimum of %s.' % minimum_carat_weight)

        color = self.color_aliases.get(cached_clean(item['stone_0_StoneHue'], upper=True))

        certifier = cached_clean(item['stone_0_StoneLab'], upper=True)

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

        clarity = cached_clean(item['stone_0_StoneClarity'], upper=True)
        if not clarity:
            raise SkipDiamond('No clarity specified')
        try:
            clarity = self.clarity_aliases[clarity]
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Clarity Aliases' % stock_number)
            raise KeyValueError('clarity', e.args[0])

        try:
            cut_grade = self.grading_aliases.get(cached_clean(item['stone_0_StoneMake'], upper=True))
        except KeyError as e:
            self.logger.info('Skipping Diamond "%s" - Cut Grade Aliases' % stock_number)
            raise KeyValueError('cut', e.args[0])

        try:
            price = Decimal(item['ItemCurrentPrice'])
            carat_price = price / Decimal(carat_weight)
        except InvalidOperation:
            carat_price = None

        if carat_price is None:
            raise SkipDiamond('No carat_price specified')

        polish = self.grading_aliases.get(cached_clean(item['stone_0_StonePolish'], upper=True))
        symmetry = self.grading_aliases.get(cached_clean(item['stone_0_StoneMajorSymmetry'], upper=True))

        fluorescence = cached_clean(item['stone_0_StoneFluor'], upper=True)
        fluorescence_id = None
        for abbr, id in self.fluorescence_aliases.iteritems():
            if fluorescence.startswith(abbr.upper()):
                fluorescence_id = id
                #fluorescence_color = fluorescence.replace(abbr.upper(), '')
                break
        fluorescence = fluorescence_id
        fluorescence_color_id = None


        depth_percent = None
        table_percent = item['stone_0_StoneTablePct']

        data = {}

        if item['stone_0_StoneLaserInscription']:
            laser_inscribed = 't'
            data.update({'stone_0_StoneLaserInscription': item['stone_0_StoneLaserInscription']})
        else:
            laser_inscribed = 'f'

        if item['ItemDetail_1']:
            data.update({'v360_link': item['ItemDetail_1']})

        if self.nvl(item['ItemDesc']):
            if self.nvl(item['ItemNotes']):
                data.update({'alt_description': item['ItemDesc'] + item['ItemNotes']})
            else:
                data.update({'alt_description': item['ItemDesc']})

        # manmade = item['stone_0_StoneNacre']   Not sure how this field is passed.

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
            'NULL', # cost,
            moneyfmt(Decimal(carat_price), curr='', sep=''),
            moneyfmt(Decimal(price), curr='', sep=''),
            certifier,
            self.nvl(item['stone_0_StoneCert']),  ## cert_num removal
            '', # cert_image,
            '', # cert_image_local,
            self.nvl(self.digits_check(depth_percent)),
            self.nvl(self.digits_check(table_percent)),
            '', # girdle,
            '', # culet,
            self.nvl(polish),
            self.nvl(symmetry),
            self.nvl(fluorescence_id),
            self.nvl(fluorescence_color_id),
            'NULL', # self.nvl(fancy_color_id),
            'NULL', # self.nvl(fancy_color_intensity_id),
            'NULL', # self.nvl(fancy_color_overtone_id),
            self.nvl(self.digits_check(item['stone_0_StoneLengthMax'])),
            self.nvl(self.digits_check(item['stone_0_StoneWidthMax'])),
            self.nvl(self.digits_check(item['stone_0_StoneDepthMax'])),
            '', # comment,
            '', #city,
            '', #state,
            '', #country,
            'f', # manmade,
            self.nvl(laser_inscribed),
            'NULL', # rap_date
            json.dumps(data),
        )

        return ret
