import logging
from optparse import make_option

from django.core.management.base import BaseCommand

from tsj_gemstone.prefs import prefs
from tsj_gemstone.utils import get_backend

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--file',
            action='store',
            dest='file',
            default=None,
            help='File to import'
        ),
        make_option('--backend',
            action='store',
            dest='backend',
            default=prefs.get('rapaport_version', 'rapaport'),
            help='Backend to import from (rapaport, rapnet10) (default: value of rapaport_version pref)',
        ),
    )

    def handle(self, *args, **options):
        backend = get_backend(options.get('backend'))
        backend.main(filename=options.get('file'))
