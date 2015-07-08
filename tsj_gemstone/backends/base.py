import logging

logger = logging.getLogger('tsj_gemstone.backends')

class SkipDiamond(Exception):
    pass

class BaseBackend(object):
    filename = None

    def __init__(self, filename=None):
        self.filename = filename
        self.backend_module = self.__module__.split('.')[-1]

    def report_missing_values(self, field, values):
        logger.error(
            'Missing values for %s' % field,
            extra={
                'tags': {
                    'backend': self.backend_module,
                },
                'missing_values': ', '.join(sorted(values)),
            },
        )

class KeyValueError(Exception):
    def __init__(self, key, value):
        self.key, self.value = key, value

    def __str__(self):
        return 'KeyValueError: %s[%s]' % (self.key, self.value)
