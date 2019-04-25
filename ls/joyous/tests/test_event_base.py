# ------------------------------------------------------------------------------
# Test Event Base
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page, PageViewRestriction
from ls.joyous.models import (EventBase, removeContentPanels, SimpleEventPage,
            MultidayEventPage, RecurringEventPage, MultidayRecurringEventPage,
            PostponementPage)
from .testutils import datetimetz, freeze_timetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def testRemoveContentPanels(self):
        removeContentPanels(["tz", "location"])
        removeContentPanels("website")

        for cls in (SimpleEventPage, MultidayEventPage, RecurringEventPage,
                    MultidayRecurringEventPage, PostponementPage):
            with self.subTest(classname = cls.__name__):
                self.assertFalse([panel for panel in cls.content_panels
                                  if getattr(panel, "field_name", None) in
                                                 ("tz", "location", "website")])

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
