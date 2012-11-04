from thinkspace.apps.ts_admin import site, ModelAdmin

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
    list_display = ('name', 'abbr', 'aliases', 'url')

class DiamondMarkupAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('percent', 'start_price', 'end_price')
    
class DiamondAdmin(ModelAdmin):
    admin_order = 2
    save_on_top = True
    list_display = ('lot_num', 'carat_weight', 'cut', 'cut_grade', 'color', 'clarity', 'formatted_carat_price', 'formatted_price', 'certifier')
    list_filter = ('cut', 'color', 'clarity', 'certifier')
    search_fields = ['lot_num', 'stock_number', 'owner', 'carat_weight', 'carat_price', 'price', 'cert_num']
    fieldsets = (
        ('Inventory', {
            'fields': (
                ('lot_num', 'stock_number', 'owner'),
                ('rap_date'),
            )
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
                ('certifier', 'cert_num', 'cert_image'),
            )
        }),
        ('Location', {
            'fields': (
                ('city', 'state', 'country'),
                ('comment'),
            )
        }),
    )

site.register(models.Cut, CutAdmin)
site.register(models.Color, ColorAdmin)
site.register(models.Clarity, ClarityAdmin)
site.register(models.Grading, GradingAdmin)
site.register(models.Fluorescence, FluorescenceAdmin)
site.register(models.FluorescenceColor, FluorescenceColorAdmin)
site.register(models.Certifier, CertifierAdmin)
site.register(models.DiamondMarkup, DiamondMarkupAdmin)
site.register(models.Diamond, DiamondAdmin)

