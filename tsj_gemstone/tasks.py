from django.db import connection

from celery import task, current_task

# FIXME: Logger.  get_task_logger or default?  Conditional on current_task?  Can we even do that?

# FIXME: Loading prefs here means values will persist until the worker process dies,
#        changes made in the admin won't be reflected.  What if we added a setting
#        to prefs to never persist values in memory?
from tsj_gemstone import backends, prefs
from tsj_gemstone.backends.base import SkipImport
from tsj_gemstone.utils import get_backend

try:
    from poc_command_overrides.management.utils import set_site
except ImportError:
    set_site = False

@task
def import_gemstone_backends(router, dry_run=False, nodebug=False, verbosity=1):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT DISTINCT db_schema FROM tsj_sites_siteinstance
        INNER JOIN information_schema.schemata ON db_schema=schema_name
        WHERE process_pool=%s
    """, (router,))

    if current_task.request.called_directly:
        for row in cursor.fetchall():
            import_site_gemstone_backends(row[0], dry_run=dry_run, nodebug=nodebug, verbosity=verbosity)
    else:
        for row in cursor.fetchall():
            import_site_gemstone_backends.delay(row[0], dry_run=dry_run, nodebug=nodebug, verbosity=verbosity)

@task
def import_site_gemstone_backends(schema, dry_run=False, nodebug=False, verbosity=1):
    assert set_site, "Failed to import set_site, is this MT?"

    if verbosity > 1:
        print 'Schema: {}'.format(schema)
    set_site({'site': schema})
    if verbosity > 2:
        print 'Gemstone prefs: {}'.format(prefs.prefs.get_dict())

    for bname in backends.__all__:
        if verbosity > 2:
            print 'Checking for {}'.format(bname)

        backend = get_backend(bname)
        backend = backend.Backend(
            nodebug=nodebug,
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
                except Exception:
                    logger.exception('Exception from backend {} for site {}'.format(bname, schema))
                    continue
