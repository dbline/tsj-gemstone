class SkipDiamond(Exception):
    pass

class BaseBackend(object):
    filename = None

    def __init__(self, filename=None):
        self.filename = filename

class KeyValueError(Exception):
    def __init__(self, key, value):
        self.key, self.value = key, value

    def __str__(self):
        return 'KeyValueError: %s[%s]' % (self.key, self.value)
