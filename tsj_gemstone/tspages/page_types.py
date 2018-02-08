from thinkspace.apps.pages.library import page_types
from thinkspace.apps.pages.page_types import PageType

from tsj_gemstone import views
from tsj_gemstone.forms import GemstoneListArgumentForm

class GemstoneList(PageType):
    view = staticmethod(views.GemstoneListView.as_view())
    argument_form = GemstoneListArgumentForm

class FancyColorGemstoneList(PageType):
    view = staticmethod(views.FancyColorGemstoneListView.as_view())

class LabGrownGemstoneList(PageType):
    view = staticmethod(views.LabGrownGemstoneListView.as_view())

class GemstoneDetail(PageType):
    view = staticmethod(views.GemstoneDetailView.as_view())
    regex_suffix = r'(?P<pk>[\d]+)/'

class GemstonePrint(PageType):
    view = staticmethod(views.GemstonePrintView.as_view())
    regex_suffix = r'(?P<pk>[\d]+)/print/'

page_types.register('gemstone-list', GemstoneList)
page_types.register('gemstone-lab-grown-list', LabGrownGemstoneList)
page_types.register('gemstone-fancy-color-list', FancyColorGemstoneList)
page_types.register('gemstone-detail', GemstoneDetail)
page_types.register('gemstone-print', GemstonePrint)
