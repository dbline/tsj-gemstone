import logging

class SkipDiamond(Exception):
    pass

class BaseBackend(object):
    filename = None

    def __init__(self, filename=None):
        self.filename = filename
        self.logger = logging.getLogger(self.__module__)

    def report_missing_values(self, field, values):
        self.logger.error('Missing values for %s: %%s' % field, ', '.join(sorted(values)))

class KeyValueError(Exception):
    def __init__(self, key, value):
        self.key, self.value = key, value

    def __str__(self):
        return 'KeyValueError: %s[%s]' % (self.key, self.value)
