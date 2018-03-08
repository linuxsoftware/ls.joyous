# ------------------------------------------------------------------------------
# Joyous Groups
# ------------------------------------------------------------------------------
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel

# ------------------------------------------------------------------------------
# Events can belong to groups
# by default joyous.GroupPage, but also designed to work with goatherd.GroupPage
# But we don't want a dependency on ls.goatherd, so make this settable
# TODO: consider using https://github.com/wq/django-swappable-models
# ------------------------------------------------------------------------------
def get_group_model_string():
    """
    Get the dotted ``app.Model`` name for the group model as a string.
    Useful for developers making Wagtail plugins that need to refer to the
    group model, such as in foreign keys, but the model itself is not required.
    """
    return getattr(settings, "JOYOUS_GROUP_MODEL", "joyous.GroupPage")


def get_group_model():
    """
    Get the group model from the ``JOYOUS_GROUP_MODEL`` setting.
    Useful for developers making Wagtail plugins that need the group model.
    Defaults to the standard :class:`~joyous.Group` model
    if no custom model is defined.
    """
    from django.apps import apps
    model_string = get_group_model_string()
    try:
        return apps.get_model(model_string)
    except ValueError:
        raise ImproperlyConfigured("JOYOUS_GROUP_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "JOYOUS_GROUP_MODEL refers to model '%s' that has not been installed" % model_string
        )

# ------------------------------------------------------------------------------
# GroupPage
# ------------------------------------------------------------------------------
class GroupPage(Page):
    subpage_types = ['joyous.SimpleEventPage',
                     'joyous.MultidayEventPage',
                     'joyous.RecurringEventPage']

    content = RichTextField(default='', blank=True)
    content.help_text = "An area of text for whatever you like"

    content_panels = Page.content_panels + [
        FieldPanel('content', classname="full"),
        ]

