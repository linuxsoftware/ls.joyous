# ------------------------------------------------------------------------------
# Test google Format
# see also test_gevents.py
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from io import BytesIO
from icalendar import vDatetime
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase, RequestFactory
from django.utils import timezone
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, CancellationPage, MultidayRecurringEventPage,
        ExtraInfoPage)
from ls.joyous.models import getAllEvents
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import WEEKLY, MONTHLY, MO, TU, WE, SA, FR
from ls.joyous.formats.google import GoogleCalendarHandler
from freezegun import freeze_time
from .testutils import datetimetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        Site.objects.update(hostname="joy.test")
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3(R3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.handler = GoogleCalendarHandler()

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    def testServeSimple(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "baseball-game",
                               title = "Baseball Game",
                               date  = dt.date(2014,7,30),
                               time_from = dt.time(13),
                               time_to   = dt.time(16),
                               tz = pytz.timezone("America/Los_Angeles"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        response = self.handler.serve(page,
                                      self._getRequest("/events/baseball-game/"
                                                       "?format=google"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "http://www.google.com/calendar/event?action=TEMPLATE&"
                         "text=Baseball+Game&dates=20140730T130000%2F20140730T160000&"
                         "ctz=America%2FLos_Angeles")

    def testServeMultiday(self):
        page = MultidayEventPage(owner = self.user,
                                 slug  = "food-festival",
                                 title = "Food Festival",
                                 date_from = dt.date(2018,11,2),
                                 date_to   = dt.date(2018,11,5),
                                 tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        response = self.handler.serve(page,
                                      self._getRequest("/events/food-festival/"
                                                       "?format=google"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "http://www.google.com/calendar/event?action=TEMPLATE&"
                         "text=Food+Festival&dates=20181102T000000%2F20181105T235959&"
                         "ctz=Pacific%2FNiue")

    def testServeRecurring(self):
        page = RecurringEventPage(owner   = self.user,
                                  slug    = "lunch-and-code",
                                  title   = "Lunch and Code",
                                  repeat    = Recurrence(dtstart=dt.date(2017,3,15),
                                                         freq=MONTHLY,
                                                         byweekday=[FR(-1)]),
                                  time_from = dt.time(12),
                                  time_to   = dt.time(13),
                                  tz = pytz.timezone("Pacific/Auckland"),
                                  location  = "70 Molesworth Street, Wellington")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        response = self.handler.serve(page,
                                      self._getRequest("/events/lunch-and-code/"
                                                       "?format=google"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "http://www.google.com/calendar/event?action=TEMPLATE&"
                         "text=Lunch+and+Code&"
                         "location=70+Molesworth+Street%2C+Wellington&"
                         "dates=20170331T120000%2F20170331T130000&"
                         "ctz=Pacific%2FAuckland&"
                         "recur=RRULE%3AFREQ%3DMONTHLY%3BWKST%3DSU%3BBYDAY%3D-1FR")

    def testServeException(self):
        event = RecurringEventPage(slug      = "test-meeting",
                                   title     = "Test Meeting",
                                   repeat    = Recurrence(dtstart=dt.date(1988,1,1),
                                                          freq=WEEKLY,
                                                          byweekday=[MO,WE,FR]),
                                   time_from = dt.time(13),
                                   time_to   = dt.time(15,30))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        info = ExtraInfoPage(owner = self.user,
                             overrides = event,
                             except_date = dt.date(1988,11,11),
                             extra_title = "System Demo",
                             extra_information = "<h3>System Demo</h3>")
        event.add_child(instance=info)
        info.save_revision().publish()
        response = self.handler.serve(info,
                                      self._getRequest("/events/test-meeting/1998-11-11/extra-info/"
                                                       "?format=google"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url,
                         "http://www.google.com/calendar/event?action=TEMPLATE&"
                         "text=Test+Meeting&"
                         "dates=19880101T130000%2F19880101T153000&"
                         "ctz=Asia%2FTokyo&"
                         "recur=RRULE%3AFREQ%3DWEEKLY%3BWKST%3DSU%3BBYDAY%3DMO%2CWE%2CFR")

    def testServeUnsupported(self):
        response = self.handler.serve(self.home, self._getRequest("/"))
        self.assertIsNone(response)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
