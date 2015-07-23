import logging
from optparse import make_option

from django.core.management.base import BaseCommand

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
        make_option('-b', '--backend',
            action='store',
            dest='backend',
            help='Backend to import from (gndiamond, polygon, rapaport, rapnet10) (default: value of rapaport_version pref)',
        ),
        make_option('--async',
            action='store_true',
            dest='async',
            help='Run this command asynchronously as a Celery task'
        ),
        make_option('--nodebug',
            action='store_true',
            dest='nodebug',
            help='Skip the "debug" test data and load real data instead',
        ),
    )

    def handle(self, *args, **options):
        # TODO: Start Celery task if async=True
        backend = get_backend(options.get('backend'))
        backend.Backend(filename=options.get('file'), nodebug=options.get('nodebug')).run()
