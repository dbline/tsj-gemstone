from django.db.models import Min, Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils import simplejson
from django.views.generic import DetailView

from thinkspace.apps.pages.views import PagesTemplateResponseMixin

from .models import Cut, Color, Clarity, Diamond, Grading, Fluorescence, FluorescenceColor, Certifier

# TODO: Move to thinkspace, probably also bring up to date with the
#       current paginator code in Django.
from tsj_catalog_local.digg_paginator import QuerySetDiggPaginator

# TODO: Move to common location.
# TODO: cache instead of thread local.
from decimal import Decimal
from math import ceil

_min_max = {}
def min_max(force_update=False):
    if force_update or not _min_max:
        _min_max['cuts'] = Cut.objects.all().order_by('order')
        _min_max['colors'] = Color.objects.all()
        _min_max['carat_weights'] = Diamond.objects.aggregate(min=Min('carat_weight'), max=Max('carat_weight'))
        _min_max['prices'] = Diamond.objects.aggregate(min=Min('price'), max=Max('price'))
        _min_max['clarities'] = Clarity.objects.exclude(abbr='N').values('order', 'name', 'abbr').order_by('order')
        _min_max['gradings'] = Grading.objects.values('order', 'name').order_by('-order')
        _min_max['fluorescence'] = Fluorescence.objects.all()
        _min_max['fluorescence_colors'] = FluorescenceColor.objects.all()
        _min_max['certifiers'] = Certifier.objects.exclude(disabled=True)
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
            print store[store_key], model_field_name
            raise Exception('Model field name is required for filter processing {0} form field.'.format(get_key))

        # Order is reversed.
        if order_rev:
            store_min_max = (store_min_max[1], store_min_max[0])
        store_type = type(store_min_max[0])

        # Floor / ceiling max and min if the stored values are Decimals or integers
        if floor_ceil:
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

def diamond_list(request, sort_by='', template='tsj_gemstone/diamond_list.html',
                 list_partial_template='tsj_gemstone/includes/list_partial.html',
                 paginator_full_partial_template='tsj_gemstone/includes/paginator_full_partial.html',
                 results_partial_template='tsj_gemstone/includes/results_partial.html',
                 extra_context={}):

    context = {
        'initial_cuts': request.GET.getlist('cut'),
    }

    diamonds = Diamond.objects.select_related('clarity', 'color', 'cut', 'cut_grade', 'certifier', 'polish', 'symmetry').order_by('carat_weight')

    min_maxs = min_max()

    if not request.is_ajax():
        #Send all of the available filter data to the template
        context.update(min_maxs)
    
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
            results_partial = render_to_string(results_partial_template, context, RequestContext(request)),
        )
        return HttpResponse(simplejson.dumps(response_dict), mimetype='application/javascript')
    else:
        return render(request, template, context)

class DiamondDetailView(PagesTemplateResponseMixin, DetailView):
    model = Diamond

    def get_queryset(self):
        qs = super(DiamondDetailView, self).get_queryset()
        qs = qs.select_related('clarity', 'color', 'cut', 'cut_grade', 'certifier', 'polish', 'symmetry')
        return qs
