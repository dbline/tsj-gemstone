from django.test import TestCase
from django.test.client import Client

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
        b = Backend(filename=Backend.debug_filename)
        results = b.run()
        self.assertEqual(results, (3488, 3268))
        self.assertEqual(Diamond.objects.count(), 3488)
