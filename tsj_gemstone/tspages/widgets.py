from django import forms
from django.db.models import Q
from django.utils.text import slugify

from ckeditor.widgets import CKEditorWidget

from thinkspace.apps.pages.library import WidgetLibrary
from thinkspace.apps.pages.widgets import TemplatedWidget
from thinkspace.apps.preferences.forms import PreferencesForm
from thinkspace.apps.pages.urlresolvers import reverse
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
    hide_gemstones=forms.MultipleChoiceField(
            label='Select gemstones to hide', 
            required=False,
            help_text='Default view is all gemstones are selected')
    icon_style = forms.ChoiceField(choices=ICON_CHOICES,
            label='Display gemstones as...', 
            required=False, 
            help_text='Gemstone icon style')
    style = forms.ChoiceField(choices=STYLE_CHOICES,
            required=False, help_text='Gemstone display style')
    show_view_all = forms.BooleanField(
            label='Show View All button',
            help_text='Shown underneath the widget',
            required=False)
    show_view_all_name = forms.CharField(
            required=False,
            label='View All button name',
            help_text='Example: View Selected Diamonds')
    show_view_all_link = forms.CharField(
            required=False,
            label='View All button URL',
            help_text='Example: /diamonds/')
    header = forms.CharField(
            widget=CKEditorWidget(config_name='advanced'),
            label='Content shown below widget title', 
            required=False)
    class_attr = forms.CharField(
            required=False,
            label='Custom widget css class(es)',
            help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
            label='Custom widget template path',
            required=False,
            help_text='Custom template file, include path and name')
    disable_images_lazy = forms.BooleanField(
            label='Disable lazy loading',
            required=False,
            help_text='When checked lazy loading attribute is not added to images used on the widget')

    fieldsections = (
        ('Format gemstones', ('hide_gemstones', 'icon_style', 'style', 'show_view_all', 'show_view_all_name', 'show_view_all_link')),
        ('Modify widget content', ('header',)),
        ('Advanced options', ('class_attr', 'template_name','disable_images_lazy')),
    )

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
    category = 'merchandise'
    verbose_name = 'Gemstones'
    description = '''Show your gemstones images or icons with links to your diamond page. You may also manage your <a href="/admin/tsj_gemstone/diamond/" target="_blank">gemstones</a>.'''

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


class MegaMenuGemstoneMaxSizeWidgetForm(PreferencesForm):
    MAX_SIZE_CHOICES = (
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
    )

    max_size = forms.ChoiceField(choices=MAX_SIZE_CHOICES,
        required=False, help_text='Gemstone max size')
    show_more_text = forms.CharField(
        label='Show More Text',
        required=False)
    show_more_url = forms.CharField(
        label='Show More URL',
        required=False,
        help_text='Leave empty to disable Show More link')
    class_attr = forms.CharField(
        required=False,
        label='CSS Class',
        help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
        required=False,
        help_text='Custom template file, include path and name')


class MegaMenuGemstoneMaxSizeWidget(TemplatedWidget):
    verbose_name = 'Gemstones Max Size'

    def render(self, context):
        context['sizes'] = self.get_sizes()
        context['show_more_text'] = self.preferences.get('show_more_text', None)
        context['show_more_url'] = self.preferences.get('show_more_url', None)
        return super(MegaMenuGemstoneMaxSizeWidget, self).render(context)

    def get_content(self):
        """
        Get a list of links for Menu Widget (not MM)
        """
        sizes = self.get_sizes()
        gemstone_list_page = reverse('gemstone-list')

        content_list = []
        if sizes:
            length = len(sizes)
            for i, size in enumerate(sizes):
                
                if i == length - 1:
                    title = '%.2f Carats & Up' % size['min']
                else:
                    title = '%.2f - %.2f Carats' % (size['min'], size['max'])

                item = {
                    'url': '%s?carat_weight_min=%.2f&carat_weight_max=%.2f' % (gemstone_list_page,
                                                                           size['min'], 
                                                                           size['max']),
                    'title': title,
                    'slug': slugify(title)
                }

                content_list.append(item)

        return content_list

    def get_sizes(self):
        max_size = int(self.preferences.get('max_size',4))
        sizes = []

        for size in range(1, max_size):
            size = float(size)
            min_value = 0.25 if size == 1 else size - 1

            sizes.append({
                'min': min_value,
                'max': size - 0.50
            })

            sizes.append({
                'min': size - 0.50,
                'max': size
            })

        sizes.append({
            'min': max_size,
            'max': 99.99
        })
        return sizes

class MegaMenuGemstoneShapesWidgetForm(PreferencesForm):

    ICON_STYLE_CHOICES = (
        ('vectors', 'Vectors'),
        ('images', 'Images'),
        ('none', 'None'),
    )

    icon_style = forms.ChoiceField(choices=ICON_STYLE_CHOICES,
        required=False, help_text='Gemstone icon style')
    hide_gemstones=forms.MultipleChoiceField(label='Hide', required=False)
    show_more_text = forms.CharField(
        label='Show More Text',
        required=False)
    show_more_url = forms.CharField(
        label='Show More URL',
        required=False,
        help_text='Leave empty to disable Show More link')
    class_attr = forms.CharField(
        required=False,
        label='CSS Class',
        help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
        required=False,
        help_text='Custom template file, include path and name')

    def __init__(self, *args, **kwargs):
        super(MegaMenuGemstoneShapesWidgetForm, self).__init__(*args, **kwargs)

        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct()
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()

        self.fields['hide_gemstones'].choices = [
            (row[0], row[1]) for row in qs.values_list('pk','name')
        ]


class MegaMenuGemstoneShapesWidget(TemplatedWidget):
    verbose_name = 'Gemstone Shapes'

    def render(self, context):
        context['widget_style'] = self.preferences.get('hide_gemstones')
        context['icon_style'] = self.preferences.get('icon_style', ICON_CHOICES[0][0])
        context['widget_object_list'] = self.get_shapes()
        context['show_more_text'] = self.preferences.get('show_more_text', None)
        context['show_more_url'] = self.preferences.get('show_more_url', None)
        return super(MegaMenuGemstoneShapesWidget, self).render(context)

    def get_content(self):
        """
        Get a list of links for Menu Widget (not MM)
        """
        shapes = self.get_shapes()
        gemstone_list_page = reverse('gemstone-list')

        content_list = []
        if shapes:
            for cut in shapes:
                item = {
                    'url': '%s?cut=%s' % (gemstone_list_page, cut.abbr),
                    'title': cut.name,
                    'slug': slugify(cut.abbr)
                }
                content_list.append(item)

        return content_list

    def get_shapes(self):
        cuts = models.Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct()
        if cuts:
            qs = models.Cut.objects.filter(id__in=cuts)
        else:
            qs = models.Cut.objects.all()

        hide_gemstones = self.preferences.get('hide_gemstones')
        if hide_gemstones:
            qs = qs.filter(~Q(id__in=hide_gemstones))

        return qs


class MegaMenuGemstoneBudgetWidgetForm(PreferencesForm):
    MAX_BUDGET_CHOICES = (
        ('3', '$3k'),
        ('4', '$4k'),
        ('5', '$5k'),
    )

    max_budget = forms.ChoiceField(choices=MAX_BUDGET_CHOICES,
        required=False, help_text='Gemstone max budget')
    show_more_text = forms.CharField(
        label='Show More Text',
        required=False)
    show_more_url = forms.CharField(
        label='Show More URL',
        required=False,
        help_text='Leave empty to disable Show More link')
    class_attr = forms.CharField(
        required=False,
        label='CSS Class',
        help_text='Separate multiple classes by spaces')
    template_name = forms.CharField(
        required=False,
        help_text='Custom template file, include path and name')


class MegaMenuGemstoneBudgetWidget(TemplatedWidget):
    verbose_name = 'Gemstones Budget'

    def render(self, context):
        context['budget'] = self.get_budget()
        context['show_more_text'] = self.preferences.get('show_more_text', None)
        context['show_more_url'] = self.preferences.get('show_more_url', None)
        return super(MegaMenuGemstoneBudgetWidget, self).render(context)

    def get_content(self):
        """
        Get a list of links for Menu Widget (not MM)
        """
        budget = self.get_budget()
        gemstone_list_page = reverse('gemstone-list')

        content_list = []
        if budget:
            length = len(budget)
            first = True
            for i, value in enumerate(budget):

                if first:
                    first = False
                    title = 'Under $%s' % value['max']
                elif i == length - 1:
                    title = '$%s &amp Up' % value['min']
                else:
                    title = '$%s - $%s' % (value['min'], value['max'])

                item = {
                    'url': '%s?price_min=%s&price_max=%s' % (gemstone_list_page, 
                                                             value['min'],
                                                             value['max']),
                    'title': title,
                    'slug': slugify(title)
                }
                content_list.append(item)

        return content_list

    def get_budget(self):
        max_budget = int(self.preferences.get('max_budget',5)) * 1000
        budget = []

        for value in range(1000, max_budget, 500):
            value = int(value)

            budget.append({
                'min': 0 if value == 1000 else value - 500,
                'max': value
            })
        budget.append({
            'min': max_budget,
            'max': 99999999
        })

        return budget

register.widget('gemstone', GemstoneWidget, form=GemstoneWidgetForm)
register.widget('megamenu-gemstone-max-size', MegaMenuGemstoneMaxSizeWidget, form=MegaMenuGemstoneMaxSizeWidgetForm)
register.widget('megamenu-gemstone-shapes', MegaMenuGemstoneShapesWidget, form=MegaMenuGemstoneShapesWidgetForm)
register.widget('megamenu-gemstone-budget', MegaMenuGemstoneBudgetWidget, form=MegaMenuGemstoneBudgetWidgetForm)
