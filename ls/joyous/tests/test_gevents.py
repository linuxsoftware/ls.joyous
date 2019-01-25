# ------------------------------------------------------------------------------
# Test google Format
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.contrib.auth.models import User
from django.test import TestCase
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage)
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import MONTHLY, FR
from ls.joyous.formats.google import (SimpleGEvent, MultidayGEvent,
        RecurringGEvent)

# ------------------------------------------------------------------------------
class TestSimple(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def testFromPage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "baseball-game",
                               title = "Baseball Game",
                               date  = dt.date(2014,7,30),
                               time_from = dt.time(13),
                               time_to   = dt.time(16),
                               tz = pytz.timezone("America/Los_Angeles"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        gev = SimpleGEvent.fromPage(page)
        self.assertEqual(gev['dates'], "20140730T130000/20140730T160000")
        self.assertEqual(gev['ctz'],   "America/Los_Angeles")

# ------------------------------------------------------------------------------
class TestMultiday(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def testFromPage(self):
        page = MultidayEventPage(owner = self.user,
                                 slug  = "kainiue-food-festival",
                                 title = "KaiNiue Food Festival",
                                 date_from = dt.date(2018,11,2),
                                 date_to   = dt.date(2018,11,5),
                                 tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        gev = MultidayGEvent.fromPage(page)
        self.assertEqual(gev['dates'], "20181102T000000/20181105T235959")
        self.assertEqual(gev['ctz'],   "Pacific/Niue")

# ------------------------------------------------------------------------------
class TestRecurring(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def testFromPage(self):
        page = RecurringEventPage(owner   = self.user,
                                  slug    = "lunch-and-code",
                                  title   = "Lunch and Code",
                                  details = "What we'll do really depends on "
                                            "what the group feels is useful, "
                                            "some ideas are:\n"
                                            "- Providing feedback on past, or "
                                            "in progress, projects\n"
                                            "- Pair programming\n"
                                            "- Coding\n",
                                  repeat    = Recurrence(dtstart=dt.date(2017,3,15),
                                                         freq=MONTHLY,
                                                         byweekday=[FR(-1)]),
                                  time_from = dt.time(12),
                                  time_to   = dt.time(13),
                                  tz = pytz.timezone("Pacific/Auckland"),
                                  location  = "70 Molesworth Street, Wellington")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        gev = RecurringGEvent.fromPage(page)
        self.assertEqual(gev.url,
                         "http://www.google.com/calendar/event?"
                         "action=TEMPLATE&"
                         "text=Lunch+and+Code&"
                         "details=What+we%27ll+do+really+depends+on+what+the+"
                         "group+feels+is+useful%2C+some+ideas+are%3A%0A"
                         "-+Providing+feedback+on+past%2C+or+in+progress%2C+projects%0A"
                         "-+Pair+programming%0A-+Coding%0A&"
                         "location=70+Molesworth+Street%2C+Wellington&"
                         "dates=20170331T120000%2F20170331T130000&"
                         "ctz=Pacific%2FAuckland&"
                         "recur=RRULE%3AFREQ%3DMONTHLY%3BWKST%3DSU%3BBYDAY%3D-1FR")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
