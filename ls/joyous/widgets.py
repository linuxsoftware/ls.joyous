# ------------------------------------------------------------------------------
# Extra widgets
# ------------------------------------------------------------------------------
import sys
import json
import datetime as dt
from wagtail.wagtailadmin.widgets import AdminTimeInput
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.forms import Media
from django.conf import settings
from django.utils import formats
from .utils.telltime import timeFormat

# ------------------------------------------------------------------------------
class Time12hrInput(AdminTimeInput):
    """
    Display and Edit time fields in a 12hr format
    """
    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)

    def format_value(self, value):
        return timeFormat(value)

    def render_js_init(self, id_, name, value):
        return "initTime12hrChooser({});".format(json.dumps(id_))

    @property
    def media(self):
        return Media(js=[static("joyous/js/time12hr_admin.js")])

# ------------------------------------------------------------------------------
if getattr(settings, "JOYOUS_TIME_INPUT", "12") in (12, "12"):
    TimeInput = Time12hrInput

    # Time12hrInput will not work unless django.forms.fields.TimeField
    # can process 12hr times, so sneak them into TIME_INPUT_FORMATS if
    # it isn't already there.  sneaky!
    _12hrFormats = ['%I:%M%p', # 2:30pm
                    '%I%p']    # 7am
    _inputFormats = formats.get_format("TIME_INPUT_FORMATS")
    if _12hrFormats[0] not in _inputFormats:
        _inputFormats += _12hrFormats
else:
    TimeInput = AdminTimeInput

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
