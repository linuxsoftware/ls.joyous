# ------------------------------------------------------------------------------
# Wagtail 2.x style EditHandlers
# ------------------------------------------------------------------------------
from django.conf import settings
from django.utils import timezone
from django.utils.formats import get_format_modules
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel
from wagtail.admin.widgets import AdminDateInput, AdminTimeInput
from .widgets import ExceptionDateInput, Time12hrInput

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
def _add12hrFormats():
    # Time12hrInput will not work unless django.forms.fields.TimeField
    # can process 12hr times, so sneak them into the default and all locales
    # TIME_INPUT_FORMATS.

    # Note: strptime does not accept %P %p is for both cases here
    _12hrFormats = ['%I:%M%p', # 2:30pm
                    '%I%p']    # 7am
    if (_12hrFormats[0] not in settings.TIME_INPUT_FORMATS or
        _12hrFormats[1] not in settings.TIME_INPUT_FORMATS):
        settings.TIME_INPUT_FORMATS += _12hrFormats

    for lang, _ in getattr(settings, 'WAGTAILADMIN_PERMITTED_LANGUAGES', []):
        for module in get_format_modules(lang):
            inputFormats = getattr(module, 'TIME_INPUT_FORMATS', [])
            if (_12hrFormats[0] not in inputFormats or
                _12hrFormats[1] not in inputFormats):
                inputFormats += _12hrFormats
                setattr(module, 'TIME_INPUT_FORMATS', inputFormats)

# ------------------------------------------------------------------------------
class TimePanel(FieldPanel):
    if getattr(settings, "JOYOUS_TIME_INPUT", "12") in (12, "12"):
        widget = Time12hrInput
        _add12hrFormats()
    else:
        widget = AdminTimeInput

# ------------------------------------------------------------------------------
class ConcealedPanel(MultiFieldPanel):
    def __init__(self, children, heading, classname='', help_text=''):
        super().__init__(children, '', classname, '')
        self._heading   = heading
        self._help_text = help_text

    def clone(self):
        return self.__class__(children=self.children,
                              heading=self._heading,
                              classname=self.classname,
                              help_text=self._help_text)

    def on_instance_bound(self):
        super().on_instance_bound()
        if self._show():
            self.heading   = self._heading
            self.help_text = self._help_text

    def render(self):
        return super().render() if self._show() else ""

    def _show(self):
        return False

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
