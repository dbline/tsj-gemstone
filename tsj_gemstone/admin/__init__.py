from functools import update_wrapper

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import site, ModelAdmin, SimpleListFilter
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _, ungettext

from .. import models
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
    list_display = ('percent', 'start_price', 'end_price')

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
    list_display = ('stock_number', 'carat_weight', 'cut', 'cut_grade', 'color', 'clarity', 'formatted_carat_price', 'formatted_price', 'certifier', 'source', 'owner', 'active')
    list_display_links = ('stock_number',)
    list_filter = ('cut', 'color', 'clarity', 'certifier', 'active', SourceFilter)
    search_fields = ['lot_num', 'stock_number', 'owner', 'carat_weight', 'carat_price', 'price', 'cert_num']

    def get_fieldsets(self, request, obj=None):
        # Initial fields
        fieldsets = (
            ('Inventory', {
                'fields': [
                    ('lot_num', 'stock_number', 'owner', 'source'),
                ]
            }),
            ('Data', {
                'fields': (
                    ('carat_weight', 'carat_price', 'price'),
                    ('cut', 'color', 'clarity'),
                    ('cut_grade'),
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
                    ['certifier', 'cert_num'],
                )
            }),
            ('Location', {
                'fields': (
                    ('city', 'state', 'country'),
                    ('comment'),
                )
            }),
        )

        if obj is None or obj.source == 'local':
            # Local diamonds have a locally uploaded certificate
            fieldsets[4][1]['fields'][0].append('cert_image_local')
        else:
            # Imported diamonds have a certificate URL
            fieldsets[4][1]['fields'][0].append('cert_image')

        if obj and obj.source in ('rapaport', 'rapnet10'):
            # Add rap_date to the Inventory section
            fieldsets[0][1]['fields'].append(('rap_date',))

        return fieldsets

    def get_urls(self):
        from django.conf.urls import url, patterns

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = patterns('',
           url('^start-import/$',
               wrap(start_import),
               name='start-gemstone-backends-import'),
        ) + super(DiamondAdmin, self).get_urls()

        return urls

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

site.register(models.Cut, CutAdmin)
site.register(models.Color, ColorAdmin)
site.register(models.Clarity, ClarityAdmin)
site.register(models.Grading, GradingAdmin)
site.register(models.Fluorescence, FluorescenceAdmin)
site.register(models.FluorescenceColor, FluorescenceColorAdmin)
site.register(models.Certifier, CertifierAdmin)
site.register(models.DiamondMarkup, DiamondMarkupAdmin)
site.register(models.Diamond, DiamondAdmin)
