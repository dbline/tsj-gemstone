from django import forms

from tinymce.widgets import TinyMCE

from thinkspace.apps.pages.library import WidgetLibrary
from thinkspace.apps.pages.widgets import TemplatedWidget
from thinkspace.apps.preferences import PreferencesForm
from tsj_gemstone import models

register = WidgetLibrary()

STYLE_CHOICES = (
    ('simple', 'Simple'),
    #('advanced', 'Advanced'),
)
class GemstoneWidgetForm(PreferencesForm):
    style = forms.ChoiceField(choices=STYLE_CHOICES,
                        required=False, help_text='Affects how the gemstones are displayed')
    header = forms.CharField(widget=TinyMCE(attrs={'cols': 80},mce_attrs={
        'width': '100%',
        'plugins': 'paste,searchreplace,style,fullscreen,nonbreaking',
        'theme_advanced_toolbar_location': 'top',
        'theme_advanced_statusbar_location': 'bottom',
        'theme_advanced_toolbar_align': 'left',
        'theme_advanced_path': True,
        'theme_advanced_buttons1': 'formatselect,bold,italic,|,justifyleft,justifycenter,justifyright,justifyfull,|,bullist,numlist,|,outdent,indent,blockquote,|,link,unlink,|,hr',
        'theme_advanced_buttons2': '',
        'extended_valid_elements': 'div[*],a[*],strong,b,em[*],i[*],ul[*],li[*],span[*],td[*],input[*]',
        'content_css': '/static/bootstrap/bootstrap/css/bootstrap.css,/static/font-awesome/css/font-awesome.css',
    }),
        required=False,
        help_text='Header content to put above the gemstones')
    class_attr = forms.CharField(
                        required=False,
                        label='CSS Class',
                        help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
                        required=False,
                        help_text='Custom template file, include path and name')

class GemstoneWidget(TemplatedWidget):
    verbose_name = 'Gemstones'
    def render(self, context):
        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct('cut__id')
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()

        context['widget_style'] = self.preferences.get('style', STYLE_CHOICES[0][0])
        context['header'] = self.preferences.get('header')
        context['widget_object_list'] = qs
        return super(GemstoneWidget, self).render(context)

register.widget('gemstone', GemstoneWidget, form=GemstoneWidgetForm)
