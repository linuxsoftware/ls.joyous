# ------------------------------------------------------------------------------
# Test ical Format
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
#from django.core import cache
from django.test import TestCase, RequestFactory
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import SimpleEventPage
from ls.joyous.formats.ical import CalendarTypeError, VCalendar
from freezegun import freeze_time
from .testutils import datetimetz

# ------------------------------------------------------------------------------
class TestVCalendar(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    @freeze_time("2018-05-12")
    def testFromCalendarPage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "bbq",
                               title = "BBQ",
                               date  = dt.date(2008,7,15),
                               time_from = dt.time(17,30),
                               time_to   = dt.time(19),
                               tz = pytz.timezone("Pacific/Auckland"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vcal = VCalendar.fromPage(self.calendar, self._getRequest("/events/"))
        export = vcal.to_ical()
        props = [b"SUMMARY:BBQ",
                 b"DTSTART;TZID=Pacific/Auckland:20080715T173000",
                 b"DTEND;TZID=Pacific/Auckland:20080715T190000",
                 b"DTSTAMP:20180512T000000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"CREATED:20180512T000000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20180512T000000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/events/bbq/",]
        for prop in props:
            with self.subTest(prop=prop.split(b'\r\n',1)[0]):
                self.assertIn(prop, export)

    @freeze_time("2018-05-12")
    def testFromEventPage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "pet-show",
                               title = "Pet Show",
                               date  = dt.date(1987,6,5),
                               time_from = dt.time(11),
                               time_to   = dt.time(17,30),
                               tz = pytz.timezone("Australia/Sydney"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vcal = VCalendar.fromPage(page, self._getRequest("/events/pet-show/"))
        export = vcal.to_ical()
        aest = b"\r\n".join([
                 b"BEGIN:STANDARD",
                 b"DTSTART;VALUE=DATE-TIME:19870315T020000",
                 b"TZNAME:AEST",
                 b"TZOFFSETFROM:+1100",
                 b"TZOFFSETTO:+1000",
                 b"END:STANDARD", ])
        aedt  = b"\r\n".join([
                 b"BEGIN:DAYLIGHT",
                 b"DTSTART;VALUE=DATE-TIME:19871025T030000",
                 b"TZNAME:AEDT",
                 b"TZOFFSETFROM:+1000",
                 b"TZOFFSETTO:+1100",
                 b"END:DAYLIGHT", ])
        props = [b"SUMMARY:Pet Show",
                 b"DTSTART;TZID=Australia/Sydney:19870605T110000",
                 b"DTEND;TZID=Australia/Sydney:19870605T173000",
                 b"DTSTAMP:20180512T000000Z",
                 b"UID:",
                 b"SEQUENCE:1",
                 b"CREATED:20180512T000000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20180512T000000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/events/pet-show/",
                 aest,
                 aedt]
        for prop in props:
            with self.subTest(prop=prop.split(b'\r\n',1)[0]):
                self.assertIn(prop, export)

    def testFromUnsupported(self):
        page = Page(owner = self.user,
                    slug  = "thoughts",
                    title = "My thoughts for today")
        self.home.add_child(instance=page)
        page.save_revision().publish()
        with self.assertRaises(CalendarTypeError):
            VCalendar.fromPage(page, self._getRequest("/thoughts/"))

    def testEmptyCalendar(self):
        vcal = VCalendar(self.calendar)
        idParts = vcal['PRODID'].split("//")
        self.assertEqual(len(idParts), 4)
        self.assertEqual(idParts[0], "-")
        self.assertEqual(idParts[1], "linuxsoftware.nz")
        self.assertEqual(idParts[2], "NONSGML Joyous v0.5")
        self.assertEqual(idParts[3], "EN")
        self.assertEqual(vcal['VERSION'], "2.0")

    def testLoad(self):
        data  = b"\r\n".join([
                b"BEGIN:VCALENDAR",
                b"VERSION:2.0",
                b"PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN",
                b"CALSCALE:GREGORIAN",
                b"METHOD:PUBLISH",
                b"X-WR-CALNAME:Bloor &amp; Spadina",
                b"X-ORIGINAL-URL:http://bloorneighbours.ca",
                b"X-WR-CALDESC:Events for Bloor &amp; Spadina",
                b"BEGIN:VEVENT",
                b"DTSTART;TZID=UTC+0:20180407T093000",
                b"DTEND;TZID=UTC+0:20180407T113000",
                b"DTSTAMP:20180402T054745",
                b"CREATED:20180304T225154Z",
                b"LAST-MODIFIED:20180304T225154Z",
                b"UID:978-1523093400-1523100600@bloorneighbours.ca",
                b"SUMMARY:Mini-Fair & Garage Sale",
                b"DESCRIPTION:",
                b"URL:http://bloorneighbours.ca/event/mini-fair-garage-sale/",
                b"END:VEVENT",
                b"END:VCALENDAR",])
        vcal = VCalendar(self.calendar)
        vcal.load(self._getRequest(), data)
        events = SimpleEventPage.events.child_of(self.calendar)            \
                                       .filter(date=dt.date(2018,4,7)).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.owner,      self.user)
        self.assertEqual(event.slug,       "mini-fair-garage-sale")
        self.assertEqual(event.title,      "Mini-Fair & Garage Sale")
        self.assertEqual(event.details,    "")
        self.assertEqual(event.date,       dt.date(2018,4,7))
        self.assertEqual(event.time_from,  dt.time(9,30))
        self.assertEqual(event.time_to,    dt.time(11,30))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
