# ------------------------------------------------------------------------------
# Joyous initialization
# ------------------------------------------------------------------------------
name = "joyous"
try:
    from ._version import version as __version__
except ImportError:  # pragma: no cover
    __version__ = '1.1'

default_app_config = 'ls.joyous.apps.JoyousAppConfig'

# ------------------------------------------------------------------------------
# Note: Default settings
# ------------------------------------------------------------------------------
# settings.JOYOUS_HOLIDAYS = ""
# settings.JOYOUS_GROUP_SELECTABLE = False
# settings.JOYOUS_GROUP_MODEL = "joyous.GroupPage"
# settings.JOYOUS_TIME_INPUT = "24"
# settings.JOYOUS_EVENTS_PER_PAGE = 25
# settings.JOYOUS_THEME_CSS = ""
# settings.JOYOUS_RSS_FEED_IMAGE = "joyous/img/logo.png"
# settings.JOYOUS_UPCOMING_INCLUDES_STARTED = False
