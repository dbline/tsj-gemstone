from thinkspace.apps.pages.library import page_types
from thinkspace.apps.pages.page_types import PageType

from tsj_gemstone import views

class DiamondList(PageType):
    view = staticmethod(views.diamond_list)

class DiamondDetail(PageType):
    view = staticmethod(views.DiamondDetailView.as_view())
    regex_suffix = r'(?P<pk>[\d-]+)/'

page_types.register('diamond-list', DiamondList)
page_types.register('diamond-detail', DiamondDetail)
