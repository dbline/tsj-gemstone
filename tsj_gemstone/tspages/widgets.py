from django import forms
from django.db.models import Q

from ckeditor.widgets import CKEditorWidget

from thinkspace.apps.pages.library import WidgetLibrary
from thinkspace.apps.pages.widgets import TemplatedWidget
from thinkspace.apps.preferences.forms import PreferencesForm
from tsj_gemstone import models

register = WidgetLibrary()

STYLE_CHOICES = (
    ('simple', 'Default'),
    #('advanced', 'Advanced'),
)
ICON_CHOICES = (
    ('vectors', 'Vectors'),
    ('images', 'Images'),
)
class GemstoneWidgetForm(PreferencesForm):
    style = forms.ChoiceField(choices=STYLE_CHOICES,
		required=False, help_text='Gemstone display style')
    icon_style = forms.ChoiceField(choices=ICON_CHOICES,
		required=False, help_text='Gemstone icon style')
    header = forms.CharField(widget=CKEditorWidget(config_name='advanced'),
        required=False,
        help_text='Header content to put above the gemstones')
    hide_gemstones=forms.MultipleChoiceField(label='Hide')
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

    def __init__(self, *args, **kwargs):
        super(GemstoneWidgetForm, self).__init__(*args, **kwargs)

        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct()
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()
        
        self.fields['hide_gemstones'].choices = [
            (row[0], row[1]) for row in qs.values_list('pk','name')
        ]

class GemstoneWidget(TemplatedWidget):
    verbose_name = 'Gemstones'

    class Media:
        js = ('tsj_gemstone/js/tsj_gemstone_widget.js',)

    def get_template_names(self, context, extra_template_names=None):
        template_names = super(GemstoneWidget, self).get_template_names(
            context, extra_template_names=extra_template_names)

        style = self.preferences.get('style')
        template_override = None
        # The default template is included by the parent method
        #if style == 'simple':
        #    template_override = 'tswidgets/tsj_gemstone.gemstone.html'
        if style == 'advanced':
            template_override = 'tswidgets/tsj_gemstone.gemstone.html'

        if template_override:
            template_names = self._template_names_with_app(template_override) + template_names

        return template_names

    def render(self, context):
        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct()
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()

        hide_gemstones = context['widget_style'] = self.preferences.get('hide_gemstones')
        if hide_gemstones:
            qs = qs.filter(~Q(id__in=hide_gemstones))

        for option in ('header', 'show_view_all', 'show_view_all_name', 'show_view_all_link', 'icon_style'):
            context[option] = self.preferences.get(option)
        context['widget_style'] = self.preferences.get('style', STYLE_CHOICES[0][0])
        context['icon_style'] = self.preferences.get('icon_style', ICON_CHOICES[0][0])
        context['widget_object_list'] = qs
        return super(GemstoneWidget, self).render(context)

register.widget('gemstone', GemstoneWidget, form=GemstoneWidgetForm)
