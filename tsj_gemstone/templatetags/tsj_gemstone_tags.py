import datetime
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from tsj_gemstone.models import Diamond

register = template.Library()

@register.simple_tag
def order_by(label, attribute, order, sort):
    if attribute == sort:
        if order == 'asc':
            ret = '<a href="?sort={attr}&order=desc">{label} <i class="fa fa-sort-asc" aria-hidden="true"></i></a>'
        else:
            ret = '<a href="?sort={attr}&order=asc">{label} <i class="fa fa-sort-desc" aria-hidden="true"></i></a>'
    else:
        ret = '<a href="?sort={attr}&order=asc">{label}</a>'

    return format_html(ret, attr=attribute, label=label)
