from django import forms
from django.db.models import Min, Max, Q

from tsj_gemstone.models import Certifier, Clarity, Color, Cut, Diamond, Fluorescence, Grading

import django_filters

class RangeChoiceWidget(forms.MultiWidget):
    def decompress(self, value):
        if value:
            return [value.start, value.stop]
        return [None, None]

class RangeChoiceField(forms.MultiValueField):
    def __init__(self, queryset=None, *args, **kwargs):
        to_field_name = kwargs.pop('to_field_name', False)
        fields = (
            forms.ModelChoiceField(queryset=queryset, to_field_name=to_field_name, **kwargs),
            forms.ModelChoiceField(queryset=queryset, to_field_name=to_field_name, **kwargs),
        )
        kwargs.pop('empty_label', False)

        defaults = {
            'widgets': [f.widget for f in fields],
        }
        widget = RangeChoiceWidget(**defaults)
        kwargs['widget'] = widget
        super(RangeChoiceField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return slice(*data_list)
        return None

class RangeChoiceFilter(django_filters.RangeFilter):
    field_class = RangeChoiceField

    def filter(self, qs, value):
        if value.start and value.stop:
            start = value.start
            stop = value.stop
            if start.id > stop.id:
                start = value.stop
                stop = value.start
            lookup = '%s__range' % self.name
            null = '%s__isnull' % self.name
            q = (Q(**{lookup: (start, stop)}) | Q(**{null: True}))
            return qs.filter(q)
        return qs

class RangeDecimalWidget(forms.MultiWidget):
    def __init__(self, attrs=None):
        if attrs:
            attrs['class'] = 'form-control'
        else:
            attrs = {'class': 'form-control'}
        widgets = (forms.TextInput(attrs=attrs), forms.TextInput(attrs=attrs))
        super(RangeDecimalWidget, self).__init__(widgets, attrs)

    def format_output(self, rendered_widgets):
        return ''.join(rendered_widgets)

class RangeDecimalField(forms.MultiValueField):
    widget = RangeDecimalWidget

    def __init__(self, fields=None, *args, **kwargs):
        if fields is None:
            fields = (
                forms.DecimalField(),
                forms.DecimalField())
        super(RangeDecimalField, self).__init__(fields, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            return slice(*data_list)
        return None

class RangeDecimalFilter(django_filters.Filter):
    field_class = RangeDecimalField

    def filter(self, qs, value):
        if value:
            if value.start and value.stop:
                lookup = '%s__range' % self.name
                return qs.filter(**{lookup: (value.start, value.stop)})
            else:
                if value.start:
                    qs = qs.filter(**{'%s__gte'%self.name:value.start})
                if value.stop:
                    qs = qs.filter(**{'%s__lte'%self.name:value.stop})
        return qs

class GemstoneFilterSet(django_filters.FilterSet):
    cut = django_filters.ModelMultipleChoiceFilter(queryset=Cut.objects.all().order_by('order'), widget=forms.CheckboxSelectMultiple, label='Shape')
    price = RangeDecimalFilter()
    carat_weight = RangeDecimalFilter(label='Carat')

    colors = Color.objects.all()
    color = RangeChoiceFilter(queryset=colors, to_field_name='abbr')

    gradings = Grading.objects.all()
    cut_grade = RangeChoiceFilter(queryset=gradings, to_field_name='name', label='Cut')
    polish = RangeChoiceFilter(queryset=gradings, to_field_name='name')
    symmetry = RangeChoiceFilter(queryset=gradings, to_field_name='name')

    clarities = Clarity.objects.all()
    clarity = RangeChoiceFilter(queryset=clarities, to_field_name='name')

    fluorescences = Fluorescence.objects.all()
    fluorescence = RangeChoiceFilter(queryset=fluorescences, to_field_name='name')

    certifiers = Certifier.objects.all().exclude(disabled=True)
    certifier = django_filters.ModelMultipleChoiceFilter(queryset=certifiers, label='Certificate')

    depth_percent = django_filters.RangeFilter(label='Depth')
    table_percent = django_filters.RangeFilter(label='Table')

    class Meta:
        fields = [
            'cut',
            'price',
            'carat_weight',
            'color',
            'cut_grade',
            'clarity',
            'certifier',
            'polish',
            'symmetry',
            'fluorescence',
            'depth_percent',
            'table_percent',
        ]
