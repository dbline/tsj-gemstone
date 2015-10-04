import logging
from optparse import make_option

from django.core.management.base import LabelCommand

from tsj_gemstone import tasks

from poc_command_overrides.management.utils import MultisiteCommand, set_site

logger = logging.getLogger('tsj_gemstone.backends')

class Command(MultisiteCommand, LabelCommand):
    args = "[router]"
    label = 'router name'
    tsj_site_option_required = False
    option_list = LabelCommand.option_list + (
        make_option('--async',
            action='store_true',
            dest='async',
            help='Run this command asynchronously as a Celery task',
        ),
        make_option('--nodebug',
            action='store_true',
            dest='nodebug',
            help='Skip the "debug" test data and load real data instead',
        ),
        make_option('-d', '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Simulate an import and log what would occur',
        )
    )

    def handle_label(self, router, **options):
        # We don't want to simply rely on CELERY_ALWAYS_EAGER here because
        # even in production (where the setting would be False) we may want
        # to run the command on the console (e.g, to see synchronous
        # verbose output)
        async = options.get('async')

        task_kwargs = {
            'dry_run': options.get('dry_run'),
            'nodebug': options.get('nodebug'),
            'verbosity': int(options.get('verbosity')),
        }

        if options.get('site'):
            # TODO: Can we avoid calling this twice when a site argument is provided?
            #       Probably, if we use the forthcoming get_schema_and_slug instead
            #       of set_site.
            one_site = self.set_site(options)

            if async:
                tasks.import_site_gemstone_backends.delay(one_site, **task_kwargs)
            else:
                tasks.import_site_gemstone_backends(one_site, **task_kwargs)
        else:
            if async:
                tasks.import_gemstone_backends.delay(router, **task_kwargs)
            else:
                tasks.import_gemstone_backends(router, **task_kwargs)
