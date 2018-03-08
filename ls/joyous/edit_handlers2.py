# ------------------------------------------------------------------------------
# Wagtail 2.x style EditHandlers
# ------------------------------------------------------------------------------
from wagtail.admin.edit_handlers import FieldPanel
from .widgets import ExceptionDateInput

# ------------------------------------------------------------------------------
class ExceptionDatePanel(FieldPanel):
    widget = ExceptionDateInput

    def on_instance_bound(self):
        super().on_instance_bound()
        widget = self.bound_field.field.widget
        widget.overrides_repeat = self.instance.overrides_repeat

# ------------------------------------------------------------------------------
