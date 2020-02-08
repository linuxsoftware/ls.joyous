# ------------------------------------------------------------------------------
# Events hooks
# ------------------------------------------------------------------------------

from django.templatetags.static import static
from django.http import HttpResponse
from django.utils.html import format_html
from wagtail.core import hooks
from wagtail.contrib.modeladmin.options import ModelAdmin
from wagtail.contrib.modeladmin.options import modeladmin_register
from .models import EventCategory, CalendarPage, CalendarPageForm
from .formats import NullHandler, ICalHandler, GoogleCalendarHandler, RssHandler

# ------------------------------------------------------------------------------
@hooks.register('before_serve_page')
def handlePageExport(page, request, serve_args, serve_kwargs):
    format = request.GET.get('format')
    if format == "ical":
        handler = ICalHandler()
    elif format == "google":
        handler = GoogleCalendarHandler()
    elif format == "rss":
        handler = RssHandler()
    else:
        handler = NullHandler()
    return handler.serve(page, request, serve_args, serve_kwargs)

@hooks.register('before_edit_page')
def stashRequest(request, page):
    if isinstance(page, CalendarPage) and CalendarPageForm.importHandler:
        page.__joyous_edit_request = request
    return None

CalendarPageForm.registerImportHandler(ICalHandler())
CalendarPageForm.registerExportHandler(ICalHandler())

# ------------------------------------------------------------------------------
class EventCategoryAdmin(ModelAdmin):
    model = EventCategory
    menu_icon = 'tag'
    menu_label = 'Event Categories'
    menu_order = 1200
    add_to_settings_menu = True
    exclude_from_explorer = False
    list_display = ('code', 'name')
    list_filter = ()
    search_fields = ('name',)

modeladmin_register(EventCategoryAdmin)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
