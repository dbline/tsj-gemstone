import json

from django.test import TestCase
from django.test.client import Client

from thinkspace.apps.pages import autodiscover

class DiamondViewsTest(TestCase):
    fixtures = (
        'tsj_gemstone/certifier.json',
        'tsj_gemstone/cut.json',
        'tsj_gemstone/color.json',
        'tsj_gemstone/clarity.json',
        'tsj_gemstone/diamond_markup.json',
        'tsj_gemstone/tests/diamond-pages.json',
        'tsj_gemstone/tests/diamonds-rapnet-0.8.json',
    )

    def setUp(self):
        autodiscover()
        self.client = Client()
        self.ajax_client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_diamond_list(self):
        response = self.client.get('/diamonds/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tsj_gemstone/diamond_list.html')

        self.assertEqual(response.context['paginator'].count, 3488)
        self.assertEqual(response.context['paginator'].num_pages, 88)
        self.assertEqual(len(response.context['page'].object_list), 40)

        # Test ajax version for pagination
        response = self.ajax_client.get('/diamonds/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertTrue(type(json.loads(response.content)), dict)

    # TODO
    def test_diamond_list_filters(self):
        """ Test the diamond list filters
        
        Filters:
        carat_weight_min=0
        carat_weight_max=5
        clarity_min=10
        clarity_max=120
        color_min=D
        color_max=Z
        cut_grade_min=10
        cut_grade_max=60
        polish_min=10
        polish_max=60
        price_min=2400
        price_max=255411
        symmetry_min=10
        symmetry_max=60
        """
        response = self.client.get('/diamonds/?color_min=F&color_max=T&clarity_min=30&clarity_max=100')
        self.assertEqual(response.context['paginator'].count, 2140)
        self.assertEqual(response.context['paginator'].num_pages, 54)
        self.assertEqual(len(response.context['page'].object_list), 40)        

    def test_diamond_detail(self):
        response = self.client.get('/diamonds/1/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tsj_gemstone/diamond_detail.html')
