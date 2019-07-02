from django.conf import settings
from django.conf.urls import url

from .views import ItemSelectView

# Gemstone saving URLs for Compare and View in Store
urlpatterns = [
    url(r'^inventory/selected/add/(?P<id>[\w-]+)/$', ItemSelectView.as_view(), {'action': 'add'}, name="selected_items_add"),
    url(r'^inventory/selected/remove/(?P<id>[\w-]+)/$', ItemSelectView.as_view(), {'action': 'remove'}, name="selected_items_remove"),
    url(r'^inventory/selected/clear/$', ItemSelectView.as_view(), {'action': 'clear'}, name="selected_items_clear"),
]
