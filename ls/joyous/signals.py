# ------------------------------------------------------------------------------
# Joyous models
# ------------------------------------------------------------------------------
import datetime as dt
from django.dispatch import receiver
from wagtail.admin.signals import init_new_page
from .models import RecurringEventPage, EventExceptionBase

# ------------------------------------------------------------------------------
# Recieve Signals
# The hook 'before_create_page' occurs too early, the page is not yet created
# so can't be modified.  The hook 'after_create_page' occurs too late, it's run
# after the form is POSTed.  
@receiver(init_new_page)
def identifyExpectantParent(sender, **kwargs):
    page = kwargs.get('page')
    parent = kwargs.get('parent')
    if (isinstance(page, EventExceptionBase) and
        isinstance(parent, RecurringEventPage) and
        not page.overrides):
        page._copyFieldsFromParent(parent)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
