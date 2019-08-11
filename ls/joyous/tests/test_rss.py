# ------------------------------------------------------------------------------
# Test RSS Format
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
        RecurringEventPage, CancellationPage, MultidayRecurringEventPage)
from ls.joyous.models import getAllEvents
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import WEEKLY, MONTHLY, TU, SA
from ls.joyous.formats.rss import RssHandler
from freezegun import freeze_time
from .testutils import datetimetz

# ------------------------------------------------------------------------------
class TestExport(TestCase):
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
        self.dicerun = SimpleEventPage(owner = self.user,
                                       slug  = "mercy-dice-run",
                                       title = "Mercy Dice Run",
                                       date  = dt.date(2020,3,16),
                                       location = "Newtown")
        self.calendar.add_child(instance=self.dicerun)
        self.dicerun.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "workshop",
                                title = "Workshop",
                                date  = dt.date(2020,3,22))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        self.handler = RssHandler()

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    def testServeCalendar(self):
        response = self.handler.serve(self.calendar,
                                      self._getRequest("/events/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), "application/xml; charset=utf-8")

    # def testServeEvent(self):
    #     response = self.handler.serve(self.dicerun,
    #                                   self._getRequest("/events/mercy-dice-run/"))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(response.get('Content-Type'), "text/calendar")
    #     self.assertEqual(response.get('Content-Disposition'),
    #                      "attachment; filename=mercy-dice-run.ics")
    #     self.assertEqual(response.content.count(b"BEGIN:VEVENT"), 1)
    #     self.assertIn(b"SUMMARY:Mercy Dice Run", response.content)
    #     self.assertIn(b"DTSTART;TZID=Asia/Tokyo:20200316T000000", response.content)
    #     self.assertIn(b"DTEND;TZID=Asia/Tokyo:20200316T235959", response.content)
    #     self.assertIn(b"LOCATION:Newtown", response.content)
    #     self.assertIn(b"URL:http://joy.test/events/mercy-dice-run", response.content)
    #
    # def testServePage(self):
    #     response = self.handler.serve(self.home, self._getRequest("/"))
    #     self.assertIsNone(response)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
