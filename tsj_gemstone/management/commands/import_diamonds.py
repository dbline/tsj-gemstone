import logging
from optparse import make_option

from django.core.management.base import BaseCommand

from tsj_gemstone.backends.rapaport import main

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    def handle(self, *args, **options):
        main()
