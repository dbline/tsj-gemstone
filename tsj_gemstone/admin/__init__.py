from django.contrib.admin import site, ModelAdmin

from .. import models

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

class DiamondMarkupAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('percent', 'start_price', 'end_price')
    
class DiamondAdmin(ModelAdmin):
    admin_order = 2
    save_on_top = True
    list_display = ('lot_num', 'carat_weight', 'cut', 'cut_grade', 'color', 'clarity', 'formatted_carat_price', 'formatted_price', 'certifier')
    list_filter = ('cut', 'color', 'clarity', 'certifier', 'source')
    search_fields = ['lot_num', 'stock_number', 'owner', 'carat_weight', 'carat_price', 'price', 'cert_num']
    exclude = ('source',)

    def get_fieldsets(self, request, obj=None):
        # Initial fields
        fieldsets = (
            ('Inventory', {
                'fields': [
                    ('lot_num', 'stock_number', 'owner'),
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

    def save_form(self, request, form, change):
        obj = form.save(commit=False)

        # Create form, which means local diamond
        if not change:
            obj.source = 'local'

        return obj

site.register(models.Cut, CutAdmin)
site.register(models.Color, ColorAdmin)
site.register(models.Clarity, ClarityAdmin)
site.register(models.Grading, GradingAdmin)
site.register(models.Fluorescence, FluorescenceAdmin)
site.register(models.FluorescenceColor, FluorescenceColorAdmin)
site.register(models.Certifier, CertifierAdmin)
site.register(models.DiamondMarkup, DiamondMarkupAdmin)
site.register(models.Diamond, DiamondAdmin)

