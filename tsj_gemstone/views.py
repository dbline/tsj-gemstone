from decimal import *
import json

from django.contrib.auth.models import User
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

from .filtersets import GemstoneFilterSet, FancyColorFilterSet
from .models import Cut, Color, Clarity, Diamond, Grading, Fluorescence, FluorescenceColor, Certifier

# TODO: Move to thinkspace, probably also bring up to date with the
#       current paginator code in Django.
from tsj_catalog_local.digg_paginator import QuerySetDiggPaginator

def _get_queryset_ordering(qs, querystring, opts):
    # Sorting
    try:
        sort = querystring.__getitem__('sort')
    except KeyError:
        sort = None

    # Order
    try:
        order = querystring.__getitem__('order')
    except KeyError:
        order = None

    try:
        opts.get_field(sort)
        if order == 'desc':
            qs = qs.order_by('-%s' % sort)
        else:
            qs = qs.order_by(sort)
    except FieldDoesNotExist:
        qs = qs.order_by('price')

    return qs

class GemstoneListView(PagesTemplateResponseMixin, ListView):
    model = Diamond
    template_name = 'tsj_gemstone/tspages/gemstone-list.html'
    no_template_name = 'tsj_gemstone/tspages/gemstone-no-list.html'
    filterset = GemstoneFilterSet

    gemstones_template = 'tsj_gemstone/includes/gemstones.html'
    pagination_template = 'tsj_gemstone/includes/pagination.html'

    def get_queryset(self):
        querystring = self.request.GET
        qs = self.model.objects.filter(active=True)
        qs = qs.select_related('clarity', 'color', 'cut', 'cut_grade', 'certifier', 'fluorescence', 'polish', 'symmetry')
        opts = self.model._meta
        qs = _get_queryset_ordering(qs, querystring, opts)
        return qs

    def get_context_data(self, **kwargs):
        context = super(GemstoneListView, self).get_context_data(**kwargs)

        q = self.request.GET.copy()

        # Sorting
        try:
            sort = q.__getitem__('sort')
        except KeyError:
            sort = None
        context['sort'] = sort

        # Order
        try:
            order = q.__getitem__('order')
        except KeyError:
            order = None
        context['order'] = order

        queryset = self.object_list

        arguments = self.request.tspages_page.get_kwargs_dict()
        # Check Source
        if arguments.get('sources'):
            sources = arguments.get('sources')
            queryset = queryset.filter(source__in=sources)

        if queryset.exists():

            # Minimum and Maximum Values
            """
            TODO: Other Cuts
            cuts = ['RD', 'PR', 'RA', 'AS', 'CU', 'OV', 'EM', 'PS', 'MQ', 'HS']
            context['cuts'] = Cut.objects.filter(abbr__in=cuts).order_by('order')
            context['other_cuts'] = Cut.objects.exclude(abbr__in=cuts).order_by('order')
            """
            distinct_cuts = Diamond.objects.values_list('cut', flat=True).order_by('cut__id').distinct('cut__id')
            context['cuts'] = Cut.objects.filter(id__in=distinct_cuts).order_by('order')
            context['colors'] = Color.objects.all().order_by('-abbr')
            context['clarities'] = Clarity.objects.all().order_by('-order')
            context['gradings'] = Grading.objects.all().order_by('-order')
            context['fluorescences'] = Fluorescence.objects.all().order_by('-order')

            aggregate = queryset.aggregate(Min('carat_weight'), Max('carat_weight'), Min('price'), Max('price'))
            carat_weights = {
                'min': aggregate['carat_weight__min'],
                'max': aggregate['carat_weight__max'],
            }
            prices = {
                'min': floatformat(aggregate['price__min'], 0),
                'max': floatformat(aggregate['price__max'], 0),
            }

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

            # Initial, Check for Carat Weight and Price
            if q.__contains__('carat_weight_0'):
                if not q.__contains__('price_0'):
                    q['price_0'] = prices['min']
                    q['price_1'] = prices['max']
                initial = q
            elif q.__contains__('price_0') and q.__contains__('price_1'):
                if not q.__contains__('carat_weight_0'):
                    q['carat_weight_0'] = carat_weights['min']
                    q['carat_weight_1'] = carat_weights['max']
                initial = q
            else:
                initial.update(q)

            filterset = self.filterset(initial, queryset=queryset)

            count = filterset.count()

            context.update({
                'carat_weights': carat_weights,
                'count': count,
                'filterset': filterset,
                'has_ring_builder': builder_prefs.get('ring'),
                'initial_cuts': self.request.GET.getlist('cut'),
                'prices': prices,
                'results': True,
                'show_prices': show_prices(self.request.user, gemstone_prefs),
                'sort': sort,
            })

            paginator = QuerySetDiggPaginator(filterset, 50, body=5, padding=2)
            try:
                paginator_page = paginator.page(self.request.GET.get('page', 1))
            except:
                paginator_page = paginator.page(paginator.num_pages)

            context.update(dict(
                paginator = paginator,
                page = paginator_page,
            ))

        else:
            context.update({
                'results': False,
            })

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
            if context['results']:
                return render(self.request, self.template_name, context)
            else:
                return render(self.request, self.no_template_name, context)

    @method_decorator(requires_csrf_token)
    def dispatch(self, *args, **kwargs):
        return super(GemstoneListView, self).dispatch(*args, **kwargs)

class FancyColorGemstoneListView(GemstoneListView):
    template_name = 'tsj_gemstone/tspages/gemstone-fancy-list.html'
    filterset = FancyColorFilterSet

    def get_queryset(self):
        return self.model.objects.filter(fancy_color__isnull=False)

class LabGrownGemstoneListView(GemstoneListView):
    def get_queryset(self):
        return self.model.objects.filter(manmade=True)

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

        if self.request.user.is_authenticated() and hasattr(self.request.user, 'account_set'):
            try:
                inquiry_form = InquiryForm(account=self.request.user.account, initial=initial)
            except User.account.RelatedObjectDoesNotExist:
                inquiry_form = InquiryForm(initial=initial)
        else:
            inquiry_form = InquiryForm(initial=initial)

        has_ring_builder = builder_prefs.get('ring')

        context['colors'] = Color.objects.all().order_by('-abbr')
        context['clarities'] = Clarity.objects.all().order_by('-order')
        context['gradings'] = Grading.objects.all().order_by('-order')

        similar_lt = float(self.object.carat_weight) - .15
        similar_gt = float(self.object.carat_weight) + .15

        similar = Diamond.objects.filter(
                    carat_weight__range=(similar_lt, similar_gt),
                    cut=self.object.cut,
                    color=self.object.color,
                    clarity=self.object.clarity).\
                    exclude(pk=self.object.pk).\
                    order_by('carat_weight', 'color', 'clarity')[:10]

        add_to_cart = gemstone_prefs.get('add_to_cart', True)

        context.update({
            'has_ring_builder': has_ring_builder,
            'inquiry_form': inquiry_form,
            'sarine_template': gemstone_prefs.get('sarine_template'),
            'show_prices': show_prices(self.request.user, gemstone_prefs),
            'add_to_cart': add_to_cart,
            'similar': similar,
        })
        return context

    @method_decorator(requires_csrf_token)
    def dispatch(self, *args, **kwargs):
        return super(GemstoneDetailView, self).dispatch(*args, **kwargs)

class GemstonePrintView(PagesTemplateResponseMixin, DetailView):
    model = Diamond
