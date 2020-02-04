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
        page.overrides = parent
        page.except_date = parent.next_date

        if isinstance(page, PostponementPage):
            # Copy across field values (should work for derieved classes too)
            parentFields = set()
            for panel in parent.content_panels:
                parentFields.update(panel.required_fields())
            pageFields = set()
            for panel in page.content_panels:
                pageFields.update(panel.required_fields())
            commonFields = parentFields & pageFields
            for name in commonFields:
                setattr(page, name, getattr(parent, name))
            if page.except_date:
                page.date           = page.except_date + dt.timedelta(days=1)
            page.postponement_title = parent.title

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
