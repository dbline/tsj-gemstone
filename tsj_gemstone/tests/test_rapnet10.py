from django.test import TestCase
from django.test.client import Client

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

    def test_backend(self):
        b = Backend(filename=Backend.debug_filename)
        results = b.run()
        self.assertEqual(results, (3797, 1))
        self.assertEqual(Diamond.objects.count(), 3797)
