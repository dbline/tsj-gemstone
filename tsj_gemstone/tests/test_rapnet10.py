from django.core.management import call_command
from django.test import TestCase

from tsj_gemstone.backends.rapnet10 import Backend
from tsj_gemstone.models import Diamond

class Rapnet10BackendTest(TestCase):
    fixtures = (
        'tsj_gemstone/certifier.json',
        'tsj_gemstone/cut.json',
        'tsj_gemstone/color.json',
        'tsj_gemstone/clarity.json',
        'tsj_gemstone/diamond_markup.json',
    )

    # TODO: Test importing a previously unknown certifier
    # TODO: Test a diamond markup not existing for a pre-markup price
    # TODO: Test invalid values for measurements
    # TODO: Test error counter and aggregator (KeyValueError, SkipDiamond)

    def test_backend(self):
        call_command('import_diamonds', backend='rapnet10', file=Backend.debug_filename)
        self.assertEqual(Diamond.objects.count(), 3797)
