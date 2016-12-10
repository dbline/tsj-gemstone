import json
from decimal import Decimal
from math import ceil

from django.db.models import Min, Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, requires_csrf_token
from django.views.generic import DetailView

from .prefs import prefs as gemstone_prefs
from thinkspace.apps.pages.views import PagesTemplateResponseMixin
from tsj_builder.prefs import prefs as builder_prefs
from tsj_commerce_local.utils import show_prices
from tsj_gemstone.models import Cut, Color, Clarity, Diamond, Grading, Fluorescence, FluorescenceColor, Certifier
from tsj_gemstone.digg_paginator import QuerySetDiggPaginator
from tsj_jewelrybox.forms import InquiryForm

_min_max = {}
def min_max(force_update=True):
    if force_update or not _min_max:
        _min_max['cuts'] = Cut.objects.all().order_by('order')
        _min_max['colors'] = Color.objects.all()
        _min_max['carat_weights'] = Diamond.objects.aggregate(min=Min('carat_weight'), max=Max('carat_weight'))
        _min_max['prices'] = Diamond.objects.aggregate(min=Min('price'), max=Max('price'))
        _min_max['clarities'] = Clarity.objects.exclude(abbr='N').values('order', 'name', 'abbr').order_by('order')
        _min_max['gradings'] = Grading.objects.values('order', 'name').order_by('-order')
        _min_max['fluorescence'] = Fluorescence.objects.all()
        _min_max['fluorescence_colors'] = FluorescenceColor.objects.all()
        certifiers = Diamond.objects.values_list('certifier', flat=True).order_by('certifier__id').distinct()
        _min_max['certifiers'] = Certifier.objects.filter(id__in=certifiers).exclude(disabled=True)

    return _min_max

def set_match(diamonds, get, get_key, store, store_key, field):
    """
    Apply given filter, if the whole set is selected, skip.
    Note that get_key is used in the filter key.
    """

    # Skip if key missing.
    if get_key in get:
        getlist = get.getlist(get_key)

        # Skip if full set
        if set(getlist) != set(store[store_key].values_list(field, flat=True)):
            return diamonds.filter(**{'{0}__{1}__in'.format(get_key, field):getlist})

    return diamonds

def full_range_match(diamonds, get, get_key, store, store_key, model_field_name=None, order_rev=False, floor_ceil=False):
    """
    Apply given filter, if the whole range is selected, skip.
    Note that the get_key is used in the filter key.
    """
    get_min_key, get_max_key = '{0}_min'.format(get_key), '{0}_max'.format(get_key)

    # Skip if key missing.
    if get_min_key in get and get_max_key in get:
        # Min means that it's an aggregate
        if 'min' in store[store_key]:
            store_min_max = (store[store_key]['min'], store[store_key]['max'])
        elif model_field_name and model_field_name in store[store_key][0]:
            count = store[store_key].count()
            store_min_max = (store[store_key][0][model_field_name], store[store_key][count-1][model_field_name])
        else:
            raise Exception('Model field name is required for filter processing {0} form field.'.format(get_key))

        # Order is reversed.
        if order_rev:
            store_min_max = (store_min_max[1], store_min_max[0])
        store_type = type(store_min_max[0])

        # Floor / ceiling max and min if the stored values are Decimals or integers
        if floor_ceil and store_min_max[0] and store_min_max[1]:
            store_min_max = (int(store_min_max[0]), int(ceil(store_min_max[1])))

        if store_type in (Decimal, int):
            store_min_max = (str(store_min_max[0]), str(store_min_max[1]))

        get_min_max = (get[get_min_key], get[get_max_key])

        # Skip if full range
        if get_min_max != store_min_max and get_min_max[0] and get_min_max[1]:
            if model_field_name:
                params = {'{0}__{1}__range'.format(get_key, model_field_name):get_min_max}
            else:
                params = {'{0}__range'.format(get_key):get_min_max}
            return diamonds.filter(**params)
    return diamonds

@csrf_protect
def gemstone_list(request, sort_by='', template='tspages/gemstone-list.html',
                 list_partial_template='tsj_gemstone/includes/list_partial.html',
                 paginator_full_partial_template='tsj_gemstone/includes/paginator_full_partial.html',
                 extra_context={}):

    has_ring_builder = builder_prefs.get('ring')

    context = {
        'has_ring_builder': has_ring_builder,
        'initial_cuts': request.GET.getlist('cut'),
        'show_prices': show_prices(request.user, gemstone_prefs),
    }

    q = request.GET

    # Sorting
    try:
        sort = q.__getitem__('sort')
    except KeyError:
        sort = None

    diamonds = Diamond.objects.filter(active=True).select_related('clarity', 'color', 'cut', 'cut_grade', 'certifier', 'polish', 'symmetry')

    if sort:
        diamonds = diamonds.order_by(sort)
    else:
        diamonds = diamonds.order_by('carat_weight', 'color', 'clarity')

    min_maxs = min_max()

    if not request.is_ajax():
        #Send all of the available filter data to the template
        context.update(min_maxs)
        context['show_lab_grown_filter'] = Diamond.objects.filter(manmade=True).exists()

    # Show lab-grown only
    if request.GET.get('manmade') == '1':
        diamonds = diamonds.filter(manmade=True)
    # Show natural only by default (0 means 'show all')
    elif request.GET.get('manmade') != '0':
        diamonds = diamonds.exclude(manmade=True)
        context['only_natural'] = True

    diamonds = set_match(diamonds, request.GET, 'cut', min_maxs, 'cuts', 'abbr')
    diamonds = full_range_match(diamonds, request.GET, 'price', min_maxs, 'prices', floor_ceil=True)
    diamonds = full_range_match(diamonds, request.GET, 'carat_weight', min_maxs, 'carat_weights')
    if request.GET.get('color_min') and request.GET.get('color_max'):
        color_list = [chr(x) for x in xrange(ord(request.GET['color_min']), ord(request.GET['color_max'])+1)]
        diamonds = diamonds.filter(color__abbr__in=color_list)
    diamonds = full_range_match(diamonds, request.GET, 'clarity', min_maxs, 'clarities', 'order')
    diamonds = set_match(diamonds, request.GET, 'certifier', min_maxs, 'certifiers', 'abbr')
    diamonds = full_range_match(diamonds, request.GET, 'cut_grade', min_maxs, 'gradings', 'order', order_rev=True)
    diamonds = full_range_match(diamonds, request.GET, 'polish', min_maxs, 'gradings', 'order', order_rev=True)
    diamonds = full_range_match(diamonds, request.GET, 'symmetry', min_maxs, 'gradings', 'order', order_rev=True)

    paginator = QuerySetDiggPaginator(diamonds, 40, body=5, padding=2)
    try: paginator_page = paginator.page(request.GET.get('page', 1))
    except: paginator_page = paginator.page(paginator.num_pages)

    context.update(dict(
        paginator = paginator,
        page = paginator_page,
    ))
    context.update(extra_context)

    if request.is_ajax():
        response_dict = dict(
            list_partial = render_to_string(list_partial_template, context, RequestContext(request)),
            paginator_full_partial = render_to_string(paginator_full_partial_template, context, RequestContext(request)),
        )
        response = HttpResponse(json.dumps(response_dict), content_type='application/javascript')
        response['Cache-Control'] = "no-cache, no-store, must-revalidate"
        return response
    else:
        return render(request, template, context)

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
