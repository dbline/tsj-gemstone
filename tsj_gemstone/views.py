from decimal import *
import json

from django.db.models import Min, Max
from django.db.models.fields import FieldDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from django.template.defaultfilters import floatformat
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, requires_csrf_token
from django.views.generic import DetailView, ListView

from .prefs import prefs as gemstone_prefs
from thinkspace.apps.pages.views import PagesTemplateResponseMixin
from tsj_builder.prefs import prefs as builder_prefs
from tsj_commerce_local.utils import show_prices
from tsj_jewelrybox.forms import InquiryForm

from .filtersets import GemstoneFilterSet
from .models import Cut, Color, Clarity, Diamond, Grading, Fluorescence, FluorescenceColor, Certifier

# TODO: Move to thinkspace, probably also bring up to date with the
#       current paginator code in Django.
from tsj_catalog_local.digg_paginator import QuerySetDiggPaginator

class GemstoneListView(PagesTemplateResponseMixin, ListView):
    model = Diamond
    template_name = 'tspages/gemstone-list.html'

    gemstones_template = 'tsj_gemstone/includes/gemstones.html'
    pagination_template = 'tsj_gemstone/includes/pagination.html'

    def get_context_data(self, **kwargs):
        context = super(GemstoneListView, self).get_context_data(**kwargs)

        q = self.request.GET

        # Sorting
        try:
            sort = q.__getitem__('sort')
        except KeyError:
            sort = None

        queryset = self.model.objects.select_related('clarity', 'color', 'cut', 'cut_grade', 'certifier', 'polish', 'symmetry')

        try:
            opts = self.model._meta
            opts.get_field(sort)
            queryset = queryset.order_by(sort)
        except FieldDoesNotExist:
            queryset = queryset.order_by('carat_weight', 'color', 'clarity')

        # Minimum and Maximum Values
        context['cuts'] = Cut.objects.all().order_by('order')
        context['colors'] = Color.objects.all().order_by('-abbr')
        carat_weights = queryset.aggregate(min=Min('carat_weight'), max=Max('carat_weight'))
        context['carat_weights'] = carat_weights
        prices = queryset.aggregate(min=Min('price'), max=Max('price'))
        prices['min'] = floatformat(prices['min'], 0)
        prices['max'] = floatformat(prices['max'], 0)
        context['prices'] = prices
        context['clarities'] = Clarity.objects.all().order_by('-order')
        context['gradings'] = Grading.objects.all().order_by('-order')
        context['fluorescences'] = Fluorescence.objects.all().order_by('-order')

        initial = {
            'price_0': prices['min'],
            'price_1': prices['max'],
            'carat_weight_0': carat_weights['min'],
            'carat_weight_1': carat_weights['max'],
            'cut_grade_0': '',
            'cut_grade_1': '',
            'color_0': '',
            'color_1': '',
            'clarity_0': '',
            'clarity_1': '',
            'polish_0': '',
            'polish_1': '',
            'symmetry_0': '',
            'symmetry_1': '',
            'fluorescence_0': '',
            'fluorescence_1': '',
        }

        # Initial
        if q.__contains__('carat_weight_0'):
            initial = q
        else:
            initial.update(q)

        filterset = GemstoneFilterSet(initial, queryset=queryset)

        context.update({
            'filterset': filterset,
            'has_ring_builder': builder_prefs.get('ring'),
            'initial_cuts': self.request.GET.getlist('cut'),
            'show_prices': show_prices(self.request.user, gemstone_prefs),
            'sort': sort,
        })

        paginator = QuerySetDiggPaginator(filterset, 40, body=5, padding=2)
        try:
            paginator_page = paginator.page(self.request.GET.get('page', 1))
        except:
            paginator_page = paginator.page(paginator.num_pages)

        context.update(dict(
            paginator = paginator,
            page = paginator_page,
        ))

        return context

    def render_to_response(self, context, **response_kwargs):
        gemstones_template = self.gemstones_template
        pagination_template = self.pagination_template

        if self.request.is_ajax():
            response_dict = dict(
                gemstones = render_to_string(gemstones_template, context, RequestContext(self.request)),
                pagination = render_to_string(pagination_template, context, RequestContext(self.request)),
            )
            response = HttpResponse(json.dumps(response_dict), content_type='application/javascript')
            response['Cache-Control'] = "no-cache, no-store, must-revalidate"
            return response
        else:
            return render(self.request, self.template_name, context)

class GemstoneDetailView(PagesTemplateResponseMixin, DetailView):
    model = Diamond

    def get_queryset(self):
        qs = super(GemstoneDetailView, self).get_queryset()
        qs = qs.select_related('clarity', 'color', 'cut', 'cut_grade', 'certifier', 'polish', 'symmetry')
        return qs

    def get_context_data(self, **kwargs):
        context = super(GemstoneDetailView, self).get_context_data(**kwargs)

        initial = {
            'item_selection': self.object.stock_number,
            'type': 'gemstone',
        }

        if self.request.user.is_authenticated():
            try:
                inquiry_form = InquiryForm(account=self.request.user.account_set.all()[0], initial=initial)
            except IndexError:
                inquiry_form = InquiryForm(initial=initial)
        else:
            inquiry_form = InquiryForm(initial=initial)

        has_ring_builder = builder_prefs.get('ring')

        context.update({
            'has_ring_builder': has_ring_builder,
            'inquiry_form': inquiry_form,
            'show_prices': show_prices(self.request.user, gemstone_prefs),
        })
        return context

    @method_decorator(requires_csrf_token)
    def dispatch(self, *args, **kwargs):
        return super(GemstoneDetailView, self).dispatch(*args, **kwargs)

class GemstonePrintView(PagesTemplateResponseMixin, DetailView):
    model = Diamond
