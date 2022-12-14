from functools import update_wrapper
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import site, ModelAdmin, SimpleListFilter
from django.core.paginator import InvalidPage, Paginator
from django.db import connection
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.translation import ugettext_lazy as _, ungettext

from .. import models
from ..prefs import prefs as prefs
from ..tasks import import_site_gemstone_backends

class CutAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'abbr', 'aliases', 'order')

class ColorAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('abbr', 'aliases')

class ClarityAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'abbr', 'aliases', 'order')

class GradingAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'abbr', 'aliases', 'order')

class FluorescenceAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'abbr', 'aliases', 'order')

class FluorescenceColorAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'abbr', 'aliases')

class FancyColorAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'aliases')

class FancyColorIntensityAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'aliases', 'order')

class FancyColorOvertoneAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'aliases')

class CertifierAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'abbr', 'aliases', 'url', 'disabled')
    actions = ModelAdmin.actions + ['action_mark_enabled', 'action_mark_disabled']

    def action_mark_enabled(self, request, queryset):
        """
        Mark as enabled action.
        """
        rows_updated = queryset.update(disabled=False)

        msg = ungettext(
            'Successfully enabled %(rows_updated)d %(name)s.',
            'Successfully enabled %(rows_updated)d %(name_plural)s.',
            rows_updated
        ) % {
            'rows_updated': rows_updated,
            'name': self.model._meta.verbose_name.title(),
            'name_plural': self.model._meta.verbose_name_plural.title()
        }
        messages.success(request, msg)
    action_mark_enabled.short_description = 'Enable selected Certifiers'

    def action_mark_disabled(self, request, queryset):
        """
        Mark as disabled action.
        """
        rows_updated = queryset.update(disabled=True)

        msg = ungettext(
            'Successfully disabled %(rows_updated)d %(name)s.',
            'Successfully disabled  %(rows_updated)d %(name_plural)s.',
            rows_updated
        ) % {
            'rows_updated': rows_updated,
            'name': self.model._meta.verbose_name.title(),
            'name_plural': self.model._meta.verbose_name_plural.title()
        }
        messages.success(request, msg)
    action_mark_disabled.short_description = 'Disable selected Certifiers'

class DiamondMarkupAdmin(ModelAdmin):
    save_on_top = True

    def get_list_display(self, request):
        if prefs.get('markup') == 'carat_weight':
            list_display = ('percent', 'minimum_carat_weight', 'maximum_carat_weight')
        else:
            list_display = ('percent', 'minimum_price', 'maximum_price')
        return list_display

    def get_fields(self, request, obj=None):
        if prefs.get('markup') == 'carat_weight':
            fields = ('minimum_carat_weight', 'maximum_carat_weight', 'percent')
        else:
            fields = ('minimum_price', 'maximum_price', 'percent')
        return fields

class SourceFilter(SimpleListFilter):
    parameter_name = 'source'
    title = _('source')

    def lookups(self, request, model_admin):
        qs = models.Diamond.objects.order_by().values_list('source', flat=True).distinct()
        ret = [(s, s) for s in qs]
        return ret

    def queryset(self, request, queryset):
        val = self.value()
        if val:
            return queryset.filter(source=val)

class DiamondAdmin(ModelAdmin):
    admin_order = 2
    save_on_top = True
    list_display = ('stock_number', 'carat_weight', 'cut', 'cut_grade', 'get_color', 'clarity', 'formatted_cost', 'formatted_carat_price', 'formatted_price', 'certifier', 'source', 'owner', 'active')
    list_display_links = ('stock_number',)
    list_filter = ('cut', 'color', 'fancy_color', 'clarity', 'certifier', 'active', SourceFilter, 'manmade')
    search_fields = ['lot_num', 'stock_number', 'owner', 'carat_weight', 'carat_price', 'price', 'cert_num']

    def get_color(self, obj):
        return obj.color or obj.fancy_color
    get_color.short_description = 'Color'
    get_color.admin_order_field = 'color'

    def get_fieldsets(self, request, obj=None):
        # Initial fields
        fieldsets = (
            ('Inventory', {
                'fields': [
                    ('active', 'lot_num', 'stock_number', 'owner', 'source'),
                ]
            }),
            ('Data', {
                'fields': (
                    ('carat_weight', 'cost', 'carat_price', 'price'),
                    ('cut', 'color', 'clarity'),
                    ('cut_grade'),
                    ('fancy_color', 'fancy_color_intensity', 'fancy_color_overtone'),
                )
            }),
            ('Measurements', {
                'fields': (
                    ('depth_percent', 'table_percent'),
                    ('length', 'width', 'depth'),
                )
            }),
            ('Misc', {
                'fields': (
                    ('polish', 'symmetry'),
                    ('girdle', 'culet'),
                    ('fluorescence', 'fluorescence_color'),
                    ('manmade',),
                )
            }),
            ('Certificate', {
                'fields': (
                    ['certifier', 'cert_num', 'cert_image', 'cert_image_local'],
                )
            }),
            ('Extra', {
                'fields': (
                    ('city', 'state', 'country'),
                    ('comment', 'data'),
                )
            }),
        )

        """
        if obj is None or obj.source == 'local':
            # Local diamonds have a locally uploaded certificate
            fieldsets[4][1]['fields'][0].append('cert_image_local')
        else:
            # Imported diamonds have a certificate URL
            fieldsets[4][1]['fields'][0].append('cert_image')
        """

        if obj and obj.source in ('rapaport', 'rapnet10'):
            # Add rap_date to the Inventory section
            fieldsets[0][1]['fields'].append(('rap_date',))

        return fieldsets

    def get_urls(self):
        from django.conf.urls import url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = [
           url('^start-import/$',
               wrap(start_import),
               name='start-gemstone-backends-import'),
           url('^import-log/$',
               wrap(import_log_list),
               name='import-log-list'),
           url('^import-log/(\d+)/$',
               wrap(import_log_detail),
               name='import-log-detail'),
        ] + super(DiamondAdmin, self).get_urls()

        return urls

    def get_queryset(self, request):
        return super(DiamondAdmin, self).get_queryset(request).select_related(
            'certifier', 'clarity', 'color', 'cut', 'fancy_color')

    def save_form(self, request, form, change):
        obj = form.save(commit=False)

        # Create form, which means local diamond
        if not change:
            obj.source = 'local'

        return obj

def start_import(request):
    sd = getattr(settings, 'SITE_DATA')
    if sd:
        import_site_gemstone_backends.delay(schema=sd.schema, nodebug=True)
    else:
        import_site_gemstone_backends.delay(nodebug=True)

    messages.info(request, 'Starting gemstone import')
    next = request.META.get('HTTP_REFERER') or '/admin/'
    return redirect(next)

def import_log_list(request, template_name='admin/tsj_gemstone/import_log_list.html'):
    sd = getattr(settings, 'SITE_DATA')
    # TODO: We shouldn't have any problem reporting imports for non-MT sites
    if not sd:
        raise Http404

    context = {
        'title': 'Gemstone Import Reports',
    }

    # TODO: While this remains a raw query, we ought to paginate in the SQL.
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, created, status, source, data
        FROM tsj_gemstone_central_import
        WHERE db_schema=%s
        ORDER BY created DESC
    """, (sd.schema,))
    rows = cursor.fetchall()
    rows_dict = []
    for row in rows:
        rows_dict.append({
            'pk': row[0],
            'created': row[1],
            'status': row[2],
            'source': row[3],
            'data': json.loads(row[4]),
        })

    paginator = Paginator(rows_dict, 100)
    page_num = int(request.GET.get('p', 0))

    try:
        page_obj = paginator.page(page_num + 1)
    except InvalidPage as e:
        raise Http404('Invalid page (%(page_num)s): %(message)s' % {
            'page_num': page_num,
            'message': str(e)
        })

    # Fake a ChangeList enough for the admin's pagination template tag
    class CL(object):
        def __init__(self, request, paginator, pn):
            self.request = request
            self.paginator = paginator
            self.page_num = pn
            self.show_all = False
            self.can_show_all = False
            self.multi_page = True

        def get_query_string(self, new_params):
            return '?{}&p={}'.format(
                self.request.META['QUERY_STRING'],
                new_params['p'],
            )

    context.update({
        'cl': CL(request, paginator, page_num),
        'page_obj': page_obj,
    })

    return render(request, template_name, context)

def import_log_detail(request, pk, template_name='admin/tsj_gemstone/import_log_detail.html'):
    sd = getattr(settings, 'SITE_DATA')
    # TODO: We shouldn't have any problem reporting imports for non-MT sites
    if not sd:
        raise Http404

    context = {
        'title': 'Gemstone Import Reports',
    }

    # TODO: While this remains a raw query, we ought to paginate in the SQL.
    cursor = connection.cursor()
    cursor.execute("""
        SELECT created, source, data
        FROM tsj_gemstone_central_import
        WHERE id=%s AND db_schema=%s
    """, (pk, sd.schema,))
    row = cursor.fetchone()
    if not row:
        raise Http404

    obj = {
        'created': row[0],
        'source': row[1],
        'data': json.loads(row[2]),
    }
    context['object'] = obj

    # Sort dicts into an ordered structure
    data = obj['data']
    if 'missing' in data:
        missing = []
        for field, value_counts in data['missing'].items():
            missing_counts = []
            for value, count in value_counts.items():
                missing_counts.append((value, count))
            missing_counts.sort(key=lambda x: x[0])
            missing.append((field, missing_counts))
        missing.sort(key=lambda x: x[0])
        context['missing'] = missing

    if 'skip' in data:
        skip = []
        for msg, count in data['skip'].items():
            skip.append((msg, count))
        skip.sort(key=lambda x: x[0])
        context['skip'] = skip

    if 'errors' in data:
        errors = []
        for msg, count in data['errors'].items():
            errors.append((msg, count))
        errors.sort(key=lambda x: x[0])
        context['errors'] = errors

    context['successes'] = data.get('successes')

    return render(request, template_name, context)

site.register(models.Cut, CutAdmin)
site.register(models.Color, ColorAdmin)
site.register(models.Clarity, ClarityAdmin)
site.register(models.Grading, GradingAdmin)
site.register(models.Fluorescence, FluorescenceAdmin)
site.register(models.FluorescenceColor, FluorescenceColorAdmin)
site.register(models.FancyColor, FancyColorAdmin)
site.register(models.FancyColorIntensity, FancyColorIntensityAdmin)
site.register(models.FancyColorOvertone, FancyColorOvertoneAdmin)
site.register(models.Certifier, CertifierAdmin)
site.register(models.DiamondMarkup, DiamondMarkupAdmin)
site.register(models.LabGrownDiamondMarkup, DiamondMarkupAdmin)
site.register(models.Diamond, DiamondAdmin)
