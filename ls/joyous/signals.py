# ------------------------------------------------------------------------------
# Joyous models
# ------------------------------------------------------------------------------
import datetime as dt
from django.dispatch import receiver
from wagtail.admin.signals import init_new_page
from .models import EventExceptionBase
from .models import RecurringEventPage, PostponementPage

# ------------------------------------------------------------------------------
# Recieve Signals
# TODO: Maybe change to @hooks.register('after_create_page')
# as it is documented and init_new_page is not?
@receiver(init_new_page)
def identifyExpectantParent(sender, **kwargs):
    page = kwargs.get('page')
    parent = kwargs.get('parent')
    if (isinstance(page, EventExceptionBase) and
        isinstance(parent, RecurringEventPage) and
        not page.overrides):
        page.overrides = parent
        page.except_date = parent.next_date

        if isinstance(page, PostponementPage):
            page.postponement_title = parent.title
            page.category           = parent.category
            page.date               = page.except_date + dt.timedelta(days=1)
            page.details            = parent.details
            page.image              = parent.image
            page.time_from          = parent.time_from
            page.time_to            = parent.time_to
            page.location           = parent.location
            page.group_page         = parent.group_page
            page.website            = parent.website

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
