from thinkspace.apps.pages.library import page_types
from thinkspace.apps.pages.page_types import PageType

from tsj_gemstone import views

class GemstoneList(PageType):
    view = staticmethod(views.gemstone_list)

class GemstoneDetail(PageType):
    view = staticmethod(views.GemstoneDetailView.as_view())
    regex_suffix = r'(?P<pk>[\d-]+)/'

page_types.register('gemstone-list', GemstoneList)
page_types.register('gemstone-detail', GemstoneDetail)
