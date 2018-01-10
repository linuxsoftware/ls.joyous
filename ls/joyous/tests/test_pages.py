import sys
from datetime import datetime
from dateutil.rrule import YEARLY, MONTHLY, WEEKLY, DAILY
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU

from django.test import TestCase
from ls.joyous.models.events import EventBase, SimpleEventPage, MultidayEventPage, RecurringEventPage

class TestPages(TestCase):
    def setUp(self):
        SimpleEventPage.objects.create
    def test_str(self):
        pass

