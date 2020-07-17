# ------------------------------------------------------------------------------
# Wagtail 2.x style EditHandlers
# ------------------------------------------------------------------------------
from django.conf import settings
from django.utils import timezone
from django.utils.formats import get_format_modules
from wagtail.admin.edit_handlers import (FieldPanel, MultiFieldPanel)
from wagtail.admin.widgets import AdminDateInput, AdminTimeInput
try:
    from wagtail.admin.localization import get_available_admin_languages
except ImportError:        # pragma: no cover
    from wagtail.admin.utils import get_available_admin_languages
from .widgets import ExceptionDateInput, Time12hrInput


# ------------------------------------------------------------------------------
class TZDatePanel(FieldPanel):
    """
    Will display the timezone of the date if it is not the current TZ
    """
    widget = AdminDateInput
    object_template = "joyous/edit_handlers/tz_date_object.html"

    def on_instance_bound(self):
        super().on_instance_bound()
        if not self.form:
            # wait for the form to be set, it will eventually be
            return
        localTZ = timezone.get_current_timezone()
        localTZName = timezone._get_timezone_name(localTZ)
        myTZ = getattr(self.instance, "tz", localTZ)
        myTZName = timezone._get_timezone_name(myTZ)
        if myTZName != localTZName:
            self.exceptionTZ = myTZName
        else:
            self.exceptionTZ = None

# ------------------------------------------------------------------------------
class ExceptionDatePanel(TZDatePanel):
    """
    Used to select from the dates of the recurrence
    """
    widget = ExceptionDateInput

    def on_instance_bound(self):
        super().on_instance_bound()
        if not self.form:
            # wait for the form to be set, it will eventually be
            return
        if not self.instance.overrides:
            return
        widget = self.form[self.field_name].field.widget
        widget.overrides_repeat = self.instance.overrides_repeat

# ------------------------------------------------------------------------------
def _add12hrFormats():
    # Time12hrInput will not work unless django.forms.fields.TimeField
    # can process 12hr times, so sneak them into the default and all the
    # selectable locales that define TIME_INPUT_FORMATS.

    # strptime does not accept %P, %p is for both cases here.
    _12hrFormats = ['%I:%M%p', # 2:30pm
                    '%I%p']    # 7am

    # TIME_INPUT_FORMATS is defined in django.conf.global_settings if not
    # by the user's local settings.
    if (_12hrFormats[0] not in settings.TIME_INPUT_FORMATS or
        _12hrFormats[1] not in settings.TIME_INPUT_FORMATS):
        settings.TIME_INPUT_FORMATS += _12hrFormats

    # Many of the built-in locales define TIME_INPUT_FORMATS
    langCodes = [language[0] for language in get_available_admin_languages()]
    langCodes.append(settings.LANGUAGE_CODE)
    for lang in langCodes:
        for module in get_format_modules(lang):
            inputFormats = getattr(module, 'TIME_INPUT_FORMATS', None)
            if (inputFormats is not None and
                (_12hrFormats[0] not in inputFormats or
                 _12hrFormats[1] not in inputFormats)):
                inputFormats += _12hrFormats

# ------------------------------------------------------------------------------
class TimePanel(FieldPanel):
    """
    Used to select time using either a 12 or 24 hour time widget
    """
    if getattr(settings, "JOYOUS_TIME_INPUT", "24") in (12, "12"):
        widget = Time12hrInput
        _add12hrFormats()
    else:
        widget = AdminTimeInput

# ------------------------------------------------------------------------------
try:
    # Use wagtailgmaps for location if it is installed
    # but don't depend upon it
    settings.INSTALLED_APPS.index('wagtailgmaps')
    from wagtailgmaps.edit_handlers import MapFieldPanel
    MapFieldPanel.UsingWagtailGMaps = True
except (ValueError, ImportError):       # pragma: no cover
    MapFieldPanel = FieldPanel

# ------------------------------------------------------------------------------
class ConcealedPanel(MultiFieldPanel):
    """
    A panel that can be hidden
    """
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
        if not self.request:
            # wait for the request to be set, it will eventually be
            return
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
