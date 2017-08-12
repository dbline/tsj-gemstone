import datetime
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

from tsj_gemstone.models import Diamond

register = template.Library()

@register.simple_tag
def order_by(label, attribute, order, sort):
    if attribute == sort:
        if order == 'asc':
            return '<a href="?sort=%s&order=desc">%s <i class="fa fa-sort-asc" aria-hidden="true"></i></a>' % (attribute, label)
        else:
            return '<a href="?sort=%s&order=asc">%s <i class="fa fa-sort-desc" aria-hidden="true"></i></a>' % (attribute, label)
    else:
        return '<a href="?sort=%s&order=asc">%s</a>' % (attribute, label)
