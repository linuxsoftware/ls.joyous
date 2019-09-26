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
from bs4 import BeautifulSoup
from django_bs_test import TestCase
from django.utils import timezone
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, CancellationPage, MultidayRecurringEventPage)
from ls.joyous.models import getAllEvents
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import WEEKLY, MONTHLY, TU, SA
from ls.joyous.formats.rss import RssHandler
from ls.joyous.formats.errors import CalendarTypeError
from freezegun import freeze_time
from .testutils import datetimetz

# ------------------------------------------------------------------------------
class TestExport(TestCase):
    @freeze_time("2016-03-24")
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
        self.event = RecurringEventPage(owner = self.user,
                                        slug  = "workshop",
                                        title = "Workshop",
                                        repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(1)],
                                                               until=dt.date(2017,12,26)),
                                       )
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()
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

    def testServeUnsupported(self):
        response = self.handler.serve(self.event,
                                      self._getRequest("/events/workshop"))
        self.assertIsNone(response)

    @freeze_time("2016-12-02")
    def testServeCalendar(self):
        response = self.handler.serve(self.calendar,
                                      self._getRequest("/events/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), "application/xml; charset=utf-8")
        self.assertIn(b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>', response.content)
        soup = BeautifulSoup(response.content, "xml")
        channel = soup.channel
        self.assertEqual(channel.title.string, "Events")
        self.assertEqual(channel.description.string, "Events")
        self.assertEqual(channel.link.string, "http://joy.test/events/")
        self.assertEqual(channel.generator.string, "ls.joyous")
        self.assertEqual(len(channel("image")), 1)
        image = channel.image
        self.assertEqual(image.url.string, "http://joy.test/static/joyous/img/logo.png")
        self.assertEqual(image.title.string, "Events")
        self.assertEqual(image.link.string, "http://joy.test/events/")
        self.assertEqual(channel.lastBuildDate.string, "Fri, 02 Dec 2016 00:00:00 +0000")
        self.assertEqual(len(channel("item")), 1)
        item = channel.item
        self.assertEqual(item.title.string, "Workshop")
        self.assertEqual(item.link.string, "http://joy.test/events/workshop/")
        self.assertEqual(item.description.string.strip(),
"""<div class="joy-ev-when joy-field">
    The first Tuesday of the month (until 26 December 2017)
  </div>\n
  <div class="joy-ev-next-on joy-field">
    Next on Tuesday 3rd of January 2017 
  </div>
\n\n\n
<div class="rich-text"></div>""")
        self.assertEqual(item.guid.get("isPermaLink"), "true")
        self.assertEqual(item.guid.string, "http://joy.test/events/workshop/")
        self.assertEqual(item.pubDate.string, "Thu, 24 Mar 2016 00:00:00 +0000")


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
