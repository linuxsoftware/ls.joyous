# ------------------------------------------------------------------------------
# Events hooks
# ------------------------------------------------------------------------------

from wagtail.contrib.modeladmin.options import ModelAdmin
from wagtail.contrib.modeladmin.options import modeladmin_register
from .models import EventCategory

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
