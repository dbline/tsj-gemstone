from django import forms

from thinkspace.apps.pages.library import WidgetLibrary
from thinkspace.apps.pages.widgets import TemplatedWidget
from thinkspace.apps.preferences import PreferencesForm
from tsj_gemstone import models

register = WidgetLibrary()

STYLE_CHOICES = ( 
    ('simple', 'Simple'),
    ('advanced', 'Advanced'),
)
class GemstoneWidgetForm(PreferencesForm):
    class_attr = forms.CharField(
                        required=False,
                        label='CSS Class',
                        help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
                        required=False,
                        help_text='Custom template file, include path and name')
    style = forms.ChoiceField(choices=STYLE_CHOICES,
                        required=False, help_text='This affects how the widget is displayed')

class GemstoneWidget(TemplatedWidget):
    verbose_name = 'Gemstones'
    def render(self, context):
        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct('cut__id')
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()

        context['widget_style'] = self.preferences.get('style', STYLE_CHOICES[0][0])
        context['widget_object_list'] = qs
        return super(GemstoneWidget, self).render(context)

register.widget('gemstone', GemstoneWidget, form=GemstoneWidgetForm)
