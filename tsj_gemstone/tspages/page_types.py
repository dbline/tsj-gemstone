from thinkspace.apps.pages.library import page_types
from thinkspace.apps.pages.page_types import PageType

from tsj_gemstone import views

class GemstoneList(PageType):
    view = staticmethod(views.gemstone_list)

class GemstoneDetail(PageType):
    view = staticmethod(views.GemstoneDetailView.as_view())
    regex_suffix = r'(?P<pk>[\d-]+)/'

class GemstonePrint(PageType):
    view = staticmethod(views.GemstonePrintView.as_view())
    regex_suffix = r'(?P<pk>[\d-]+)/print/'

page_types.register('gemstone-list', GemstoneList)
page_types.register('gemstone-detail', GemstoneDetail)
page_types.register('gemstone-print', GemstonePrint)
