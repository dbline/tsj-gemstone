import logging
from optparse import make_option

from django.core.management.base import LabelCommand
from django.db import connection

from tsj_gemstone import backends, prefs
from tsj_gemstone.backends.base import SkipImport
from tsj_gemstone.utils import get_backend

from poc_command_overrides.management.utils import set_site

class Command(LabelCommand):
    args = "[router]"
    label = 'router name'
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
        verbosity = int(options.get('verbosity'))
        dry_run = options.get('dry_run')

        cursor = connection.cursor()
        cursor.execute("""
            SELECT DISTINCT db_schema FROM tsj_sites_siteinstance
            INNER JOIN information_schema.schemata ON db_schema=schema_name
            WHERE process_pool=%s
        """, (router,))

        for row in cursor.fetchall():
            schema = row[0]
            if verbosity > 1:
                print 'Schema: {}'.format(schema)
            set_site({'site': row[0]})
            if verbosity > 2:
                print 'Gemstone prefs: {}'.format(prefs.prefs.get_dict())

            for bname in backends.__all__:
                if verbosity > 2:
                    print 'Checking for {}'.format(bname)

                backend = get_backend(bname)
                backend = backend.Backend(
                    nodebug=options.get('nodebug'),
                )

                if backend.enabled:
                    if verbosity > 1:
                        if dry_run:
                            print 'Would run {}'.format(bname)
                        else:
                            print 'Running {}'.format(bname)
                    if not dry_run:
                        try:
                            backend.run()
                        except SkipImport:
                            if verbosity > 1:
                                print 'Skipping {}'.format(bname)
                            continue
