# ------------------------------------------------------------------------------
# Joyous Groups
# ------------------------------------------------------------------------------
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel

# ------------------------------------------------------------------------------
# Events can belong to groups
# by default joyous.GroupPage, but also designed to work with goatherd.GroupPage
# But we don't want a dependency on ls.goatherd, so make this settable
# ------------------------------------------------------------------------------
def get_group_model_string():
    """
    Get the dotted ``app.Model`` name for the group model as a string.
    Useful for developers that need to refer to the group model, such as in
    foreign keys, but the model itself is not required.
    """
    return getattr(settings, "JOYOUS_GROUP_MODEL", "joyous.GroupPage")


def get_group_model():
    """
    Get the group model from the ``JOYOUS_GROUP_MODEL`` setting.
    Useful for developers that need the group model.
    Defaults to the standard :class:`ls.joyous.models.GroupPage` model
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
    class Meta:
        verbose_name = _("group page")
        verbose_name_plural = _("group pages")

    # Define page_ptr so the related_name doesn't clash
    page_ptr = models.OneToOneField(Page, on_delete=models.CASCADE,
                                    related_name="%(app_label)s_%(model_name)s",
                                    parent_link=True)

    subpage_types = ['joyous.SimpleEventPage',
                     'joyous.MultidayEventPage',
                     'joyous.RecurringEventPage',
                     'joyous.MultidayRecurringEventPage']

    content = RichTextField(_("content"), default='', blank=True)
    content.help_text = _("An area of text for whatever you like")

    content_panels = Page.content_panels + [
        FieldPanel('content', classname="full"),
        ]

    def get_context(self, request, *args, **kwargs):
        retval = super().get_context(request, *args, **kwargs)
        retval['themeCSS'] = getattr(settings, "JOYOUS_THEME_CSS", "")
        return retval

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
