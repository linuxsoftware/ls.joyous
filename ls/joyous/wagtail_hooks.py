# ------------------------------------------------------------------------------
# Events hooks
# ------------------------------------------------------------------------------

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import format_html
from wagtail.wagtailcore import hooks
from wagtail.contrib.modeladmin.options import ModelAdmin
from wagtail.contrib.modeladmin.options import modeladmin_register
from .models import EventCategory

# ------------------------------------------------------------------------------
@hooks.register('insert_editor_js')
def editor_js():
    return format_html(
        '<script src="{}"></script>',
        static('joyous/js/vendor/moment-2.22.0.min.js')
    )

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
