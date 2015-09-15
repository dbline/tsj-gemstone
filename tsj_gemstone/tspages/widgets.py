from django import forms

from tinymce.widgets import TinyMCE

from thinkspace.apps.pages.library import WidgetLibrary
from thinkspace.apps.pages.widgets import TemplatedWidget
from thinkspace.apps.preferences import PreferencesForm
from tsj_gemstone import models

register = WidgetLibrary()

STYLE_CHOICES = (
    ('simple', 'Default'),
    #('advanced', 'Advanced'),
)
ICON_CHOICES = (
    ('vectors', 'Vector'),
    ('images', 'Images'),
)
class GemstoneWidgetForm(PreferencesForm):
    style = forms.ChoiceField(choices=STYLE_CHOICES,
		required=False, help_text='Gemstone display style')
    icon_style = forms.ChoiceField(choices=ICON_CHOICES,
		required=False, help_text='Gemstone icon style')
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
    show_view_all = forms.BooleanField(
        label='Show View All Button',
        required=False)
    show_view_all_name = forms.CharField(
        required=False,
        label='Button Name',
        help_text='View All Button Name')
    show_view_all_link = forms.CharField(
        required=False,
        label='URL',
        help_text='View All URL')
    class_attr = forms.CharField(
		required=False,
		label='CSS Class',
		help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
		required=False,
		help_text='Custom template file, include path and name')

class GemstoneWidget(TemplatedWidget):
    verbose_name = 'Gemstones'

    def get_template_names(self, context, extra_template_names=None):
        template_names = super(GemstoneWidget, self).get_template_names(
            context, extra_template_names=extra_template_names)

        style = self.preferences.get('style')
        if style == 'simple':
            template_names.insert(0, 'tswidgets/tsj_gemstone.gemstone.html')
        elif style == 'advanced':
            template_names.insert(0, 'tswidgets/tsj_gemstone.gemstone.html')
        return template_names

    def render(self, context):
        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct('cut__id')
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()

        for option in ('header', 'show_view_all', 'show_view_all_name', 'show_view_all_link', 'icon_style'):
            context[option] = self.preferences.get(option)
        context['widget_style'] = self.preferences.get('style', STYLE_CHOICES[0][0])
        context['widget_object_list'] = qs
        return super(GemstoneWidget, self).render(context)

register.widget('gemstone', GemstoneWidget, form=GemstoneWidgetForm)
