# ------------------------------------------------------------------------------
# Wagtail 2.x style EditHandlers
# ------------------------------------------------------------------------------
from django.utils import timezone
from wagtail.admin.edit_handlers import FieldPanel
from .widgets import ExceptionDateInput

# ------------------------------------------------------------------------------
class ExceptionDatePanel(FieldPanel):
    widget = ExceptionDateInput
    object_template = "joyous/edit_handlers/exception_date_object.html"

    def on_instance_bound(self):
        super().on_instance_bound()
        widget = self.bound_field.field.widget
        widget.overrides_repeat = self.instance.overrides_repeat
        tz = timezone._get_timezone_name(self.instance.tz)
        if tz != timezone.get_current_timezone_name():
            self.exceptionTZ = tz
        else:
            self.exceptionTZ = None


# ------------------------------------------------------------------------------
class ImportCalendarPanel(FieldPanel):
    pass

# ------------------------------------------------------------------------------
class ExportCalendarPanel(FieldPanel):
    pass

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
