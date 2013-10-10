from django.core.management import call_command
from django.test import TestCase

from tsj_gemstone.backends.rapaport import Backend
from tsj_gemstone.models import Diamond

class RapaportBackendTest(TestCase):
    fixtures = (
        'tsj_gemstone/certifier.json',
        'tsj_gemstone/cut.json',
        'tsj_gemstone/color.json',
        'tsj_gemstone/clarity.json',
        'tsj_gemstone/diamond_markup.json',
    )

    def test_backend(self):
        call_command('import_diamonds', backend='rapaport', file=Backend.debug_filename)
        self.assertEqual(Diamond.objects.count(), 3488)
