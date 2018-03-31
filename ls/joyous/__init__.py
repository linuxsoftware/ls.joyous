# ------------------------------------------------------------------------------
# Joyous initialization
# ------------------------------------------------------------------------------
name = "joyous"
try:
    from ._version import version as __version__
except ImportError:
    __version__ = 'unknown'

from .utils import wagtailcompat

default_app_config = 'ls.joyous.apps.JoyousAppConfig'

# ------------------------------------------------------------------------------
# Note: Default settings
# ------------------------------------------------------------------------------
# settings.JOYOUS_DEFAULT_EVENTS_VIEW = "Monthly"
# settings.JOYOUS_HOLIDAYS = ""
# settings.JOYOUS_GROUP_SELECTABLE = False
# settings.JOYOUS_GROUP_MODEL = "joyous.GroupPage"
# settings.JOYOUS_TIME_INPUT = "12"
