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

def diamond_list(request, sort_by='', template='tsj_gemstone/diamond_list.html',
                 list_partial_template='tsj_gemstone/includes/list_partial.html',
                 paginator_full_partial_template='tsj_gemstone/includes/paginator_full_partial.html',
                 results_partial_template='tsj_gemstone/includes/results_partial.html',
                 extra_context={}):

    context = {}

    diamonds = Diamond.objects.select_related().order_by('carat_weight')

    if not request.is_ajax():
        #Send all of the available filter data to the template
        cuts = Cut.objects.all().order_by('order')
        colors = Color.objects.all()
        carat_weights = Diamond.objects.aggregate(min=Min('carat_weight'), max=Max('carat_weight'))
        prices = Diamond.objects.aggregate(min=Min('price'), max=Max('price'))
        clarities = Clarity.objects.exclude(abbr='N').values('order', 'name', 'abbr').order_by('order')
        gradings = Grading.objects.values('order', 'name').order_by('-order')
        fluorescence = Fluorescence.objects.all()
        fluorescence_colors = FluorescenceColor.objects.all()
        certifiers = Certifier.objects.exclude(abbr='NONE')
        context.update(dict(
            cuts = cuts,
            gradings = gradings,
            colors = colors,
            carat_weights = carat_weights,
            prices = prices,
            clarities = clarities,
            fluorescence = fluorescence,
            fluorescence_colors = fluorescence_colors,
            certifiers = certifiers,
        ))
    
    #FIXME: For some reason, the number of pages available on load and the number availabled after picking a page other than 1 are different. There are some filters that are getting applied when the form serializes via jQuery that aren't getting applied upon the diamond list page's load
    if 'cut' in request.GET: diamonds = diamonds.filter(cut__abbr__in=request.GET.getlist('cut'))
    if 'price_min' and 'price_max' in request.GET: diamonds = diamonds.filter(price__range=(request.GET['price_min'], request.GET['price_max']))
    if 'carat_weight_min' and 'carat_weight_max' in request.GET: diamonds = diamonds.filter(carat_weight__range=(request.GET['carat_weight_min'], request.GET['carat_weight_max']))
    if 'color_min' and 'color_max' in request.GET:
        color_list = [chr(x) for x in xrange(ord(request.GET['color_min']), ord(request.GET['color_max'])+1)]
        diamonds = diamonds.filter(color__abbr__in=color_list)
    if 'clarity_min' and 'clarity_max' in request.GET: diamonds = diamonds.filter(clarity__order__range=(request.GET['clarity_min'], request.GET['clarity_max']))
    if 'certifier' in request.GET: diamonds = diamonds.filter(certifier__abbr__in=request.GET.getlist('certifier'))
    if 'cut_grade_min' and 'cut_grade_max' in request.GET: diamonds = diamonds.filter(cut_grade__order__range=(request.GET['cut_grade_min'], request.GET['cut_grade_max']))
    if 'polish_min' and 'polish_max' in request.GET: diamonds = diamonds.filter(polish__order__range=(request.GET['polish_min'], request.GET['polish_max']))
    if 'symmetry_min' and 'symmetry_max' in request.GET: diamonds = diamonds.filter(symmetry__order__range=(request.GET['symmetry_min'], request.GET['symmetry_max']))

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
