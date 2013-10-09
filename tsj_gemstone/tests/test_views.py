from django.test import TestCase
from django.test.client import Client

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
        self.client = Client()

    def test_diamond_list(self):
        response = self.client.get('/diamonds/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tsj_gemstone/diamond_list.html')

        self.assertEqual(response.context['paginator'].count, 3488)
        self.assertEqual(response.context['paginator'].num_pages, 88)
        self.assertEqual(len(response.context['page'].object_list), 40)

    # TODO
    def test_diamond_list_filters(self):
        pass

    def test_diamond_detail(self):
        response = self.client.get('/diamonds/1/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tsj_gemstone/diamond_detail.html')
