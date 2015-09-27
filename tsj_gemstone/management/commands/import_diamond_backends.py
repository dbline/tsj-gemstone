import logging
from optparse import make_option

from django.core.management.base import LabelCommand
from django.db import connection

from tsj_gemstone import backends, prefs
from tsj_gemstone.backends.base import SkipImport
from tsj_gemstone.utils import get_backend

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
        self.verbosity = int(options.get('verbosity'))
        self.nodebug = options.get('nodebug')
        self.dry_run = options.get('dry_run')
        async = options.get('async')

        # Check if a site argument was provided
        # TODO: Can we avoid calling this twice when a site argument is provided?
        one_site = self.set_site(options)

        if one_site:
            self.handle_for_site(one_site)
        else:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT DISTINCT db_schema FROM tsj_sites_siteinstance
                INNER JOIN information_schema.schemata ON db_schema=schema_name
                WHERE process_pool=%s
            """, (router,))

            if async:
                for row in cursor.fetchall():
                    #handle_for_site.delay(row[0])
                    pass
            else:
                for row in cursor.fetchall():
                    self.handle_for_site(row[0])

    def handle_for_site(self, schema):
        if self.verbosity > 1:
            print 'Schema: {}'.format(schema)
        set_site({'site': schema})
        if self.verbosity > 2:
            print 'Gemstone prefs: {}'.format(prefs.prefs.get_dict())

        for bname in backends.__all__:
            if self.verbosity > 2:
                print 'Checking for {}'.format(bname)

            backend = get_backend(bname)
            backend = backend.Backend(
                nodebug=self.nodebug,
            )

            if backend.enabled:
                if self.verbosity > 1:
                    if self.dry_run:
                        print 'Would run {}'.format(bname)
                    else:
                        print 'Running {}'.format(bname)
                if not self.dry_run:
                    try:
                        backend.run()
                    except SkipImport:
                        if self.verbosity > 1:
                            print 'Skipping {}'.format(bname)
                    except Exception:
                        logger.exception('Exception from backend {} for site {}'.format(bname, schema))
                        continue
