import logging

from django.conf import settings

from ..prefs import prefs

logger = logging.getLogger('tsj_gemstone.backends')
summary_logger = logging.getLogger('tsj_gemstone.backends.summary')

class SkipDiamond(Exception):
    pass

class SkipImport(Exception):
    pass

class BaseBackend(object):
    filename = None

    def __init__(self, filename=None, nodebug=False):
        self.filename = filename
        self.backend_module = self.__module__.split('.')[-1]
        self.nodebug = nodebug

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

class KeyValueError(Exception):
    def __init__(self, key, value):
        self.key, self.value = key, value

    def __str__(self):
        return 'KeyValueError: %s[%s]' % (self.key, self.value)
