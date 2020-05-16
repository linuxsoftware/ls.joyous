# ------------------------------------------------------------------------------
# Test ical Format
# see also test_vevents.py, test_vutils.py and test_vcalendar.py
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from io import BytesIO
from icalendar import vDatetime
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib import messages
from django.test import TestCase, RequestFactory
from django.utils import timezone
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, CancellationPage, MultidayRecurringEventPage,
        RescheduleMultidayEventPage)
from ls.joyous.models import getAllEvents
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import WEEKLY, MONTHLY, TU, SA
from ls.joyous.formats.ical import ICalHandler
from freezegun import freeze_time
from .testutils import datetimetz

# ------------------------------------------------------------------------------
class TestImport(TestCase):
    def setUp(self):
        Site.objects.update(hostname="joy.test")
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.handler = ICalHandler()

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    @freeze_time("2018-07-24 19:00:00")
    def testMeetup(self):
        stream = BytesIO(b"""\
BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:-//Meetup//RemoteApi//EN\r
CALSCALE:GREGORIAN\r
METHOD:PUBLISH\r
X-ORIGINAL-URL:https://www.meetup.com/Code-for-Boston/events/249894034/ic\r
 al/Weekly+Hack+Night.ics\r
X-WR-CALNAME:Events - Weekly Hack Night.ics\r
X-MS-OLK-FORCEINSPECTOROPEN:TRUE\r
BEGIN:VTIMEZONE\r
TZID:America/New_York\r
X-LIC-LOCATION:America/New_York\r
BEGIN:DAYLIGHT\r
TZOFFSETFROM:-0500\r
TZOFFSETTO:-0400\r
TZNAME:EDT\r
DTSTART:19700308T020000\r
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r
END:DAYLIGHT\r
BEGIN:STANDARD\r
TZOFFSETFROM:-0400\r
TZOFFSETTO:-0500\r
TZNAME:EST\r
DTSTART:19701101T020000\r
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r
END:STANDARD\r
END:VTIMEZONE\r
BEGIN:VEVENT\r
DTSTAMP:20180721T015100Z\r
DTSTART;TZID=America/New_York:20180724T190000\r
DTEND;TZID=America/New_York:20180724T213000\r
STATUS:CONFIRMED\r
SUMMARY:Weekly Hack Night\r
DESCRIPTION:Code for Boston\\nTuesday\\, July 24 at 7:00 PM\\n\\nOur weekly w\r
 ork session will be at the Cambridge Innovation Center in Kendall Square\r
 \\, on the FOURTH FLOOR\\, in the CAFE. These Hack Nights are our time...\\\r
 n\\nhttps://www.meetup.com/Code-for-Boston/events/249894034/\r
CLASS:PUBLIC\r
CREATED:20180404T010420Z\r
GEO:42.36;-71.09\r
LOCATION:Cambridge Innovation Center\\, 4th Floor Cafe (1 Broadway\\, Cambr\r
 idge\\, MA)\r
URL:https://www.meetup.com/Code-for-Boston/events/249894034/\r
LAST-MODIFIED:20180404T010420Z\r
UID:event_xwqmnpyxkbgc@meetup.com\r
END:VEVENT\r
END:VCALENDAR""")
        self.handler.load(self.calendar, self._getRequest(), stream)
        events = SimpleEventPage.events.child_of(self.calendar).all()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.owner,      self.user)
        self.assertEqual(event.slug,       "weekly-hack-night")
        self.assertEqual(event.title,      "Weekly Hack Night")
        self.assertEqual(event.details,    "\n".join(["Code for Boston",
            "Tuesday, July 24 at 7:00 PM", "",
            "Our weekly work session will be at the Cambridge Innovation Center in Kendall Square"
            ", on the FOURTH FLOOR, in the CAFE. These Hack Nights are our time...", "",
            "https://www.meetup.com/Code-for-Boston/events/249894034/"]))
        self.assertEqual(event.date,       dt.date(2018,7,24))
        self.assertEqual(event.time_from,  dt.time(19))
        self.assertEqual(event.time_to,    dt.time(21,30))
        self.assertEqual(event.tz.zone,    "America/New_York")

    @freeze_time("2018-02-01")
    @timezone.override("Pacific/Auckland")
    def testGoogleCalendar(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Test Data
X-WR-TIMEZONE:Pacific/Auckland
X-WR-CALDESC:Sample data for Joyous test_ical unittest
BEGIN:VTIMEZONE
TZID:Pacific/Auckland
X-LIC-LOCATION:Pacific/Auckland
BEGIN:DAYLIGHT
TZOFFSETFROM:+1200
TZOFFSETTO:+1300
TZNAME:NZDT
DTSTART:19700927T020000
RRULE:FREQ=YEARLY;BYMONTH=9;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+1300
TZOFFSETTO:+1200
TZNAME:NZST
DTSTART:19700405T030000
RRULE:FREQ=YEARLY;BYMONTH=4;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
DTSTART:20180725T210000Z
DTEND:20180726T083000Z
DTSTAMP:20180722T060025Z
UID:1uas8vo82gvhtn8jpr9nlnrmfk@google.com
CREATED:20180722T035919Z
DESCRIPTION:Hounit <b>catlike</b> at ethatial to thin a usistiques onshiend
  alits mily tente duse prommuniss ind sedships itommunte of perpollood.
LAST-MODIFIED:20180722T035919Z
LOCATION:
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Big Thursday
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Pacific/Auckland:20180703T093000
DTEND;TZID=Pacific/Auckland:20180703T113000
RRULE:FREQ=WEEKLY;UNTIL=20180828T115959Z;BYDAY=TU
EXDATE;TZID=Pacific/Auckland:20180814T093000
DTSTAMP:20180722T060025Z
UID:113qbmq1j4jf0jbiolheruff6n@google.com
CREATED:20180722T035429Z
DESCRIPTION:\nFammulturacha matent theaminerviencess atinjuse it shin sue o
 f Aothips to ming an sed prage thnisithass invernships oftegruct and encome
 . Taimen in grose to to ner grough ingin orgagences' of Fries seed\n\nFrith
 erovere Houps of custims analienessuppol. Tiriendindnew\, vality a gruccous
 er to be the juse Truch ince lity Te therneramparcialues the the neshipland
 s tortandamength\,  Comene ups a mitioney dend peachassfy de are to entices
  meand evelas of Friscerple th iseek arces a wind.
LAST-MODIFIED:20180722T035937Z
LOCATION:Coast Rd\, Barrytown\, New Zealand
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Tuesday Mornings
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20180713
DTEND;VALUE=DATE:20180716
DTSTAMP:20180722T060025Z
UID:01likr2u3bchpv66o7vvq23avq@google.com
CREATED:20180722T040054Z
DESCRIPTION:
LAST-MODIFIED:20180722T040054Z
LOCATION:Home
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Three days off
TRANSP:TRANSPARENT
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Pacific/Auckland:20180725T093000
DTEND;TZID=Pacific/Auckland:20180725T113000
DTSTAMP:20180722T060025Z
UID:113qbmq1j4jf0jbiolheruff6n@google.com
RECURRENCE-ID;TZID=Pacific/Auckland:20180724T093000
CREATED:20180722T035429Z
DESCRIPTION:\nFammulturacha matent theaminerviencess atinjuse it shin sue o
 f Aothips to ming an sed prage thnisithass invernships oftegruct and encome
 . Taimen in grose to to ner grough ingin orgagences' of Fries seed\n\nFrith
 erovere Houps of custims analienessuppol. Tiriendindnew\, vality a gruccous
 er to be the juse Truch ince lity Te therneramparcialues the the neshipland
 s tortandamength\,  Comene ups a mitioney dend peachassfy de are to entices
  meand evelas of Friscerple th iseek arces a wind.
LAST-MODIFIED:20180722T051000Z
LOCATION:Coast Rd\, Barrytown\, New Zealand
SEQUENCE:1
STATUS:CONFIRMED
SUMMARY:Tuesday Mornings Postponed
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
DTSTART;TZID=Pacific/Auckland:20180731T093000
DTEND;TZID=Pacific/Auckland:20180731T113000
DTSTAMP:20180722T060025Z
UID:113qbmq1j4jf0jbiolheruff6n@google.com
RECURRENCE-ID;TZID=Pacific/Auckland:20180731T093000
CREATED:20180722T035429Z
DESCRIPTION:\nExtra Famin fork\, andivery\,  Hough in the re of re whels ot
 edshiplue porturat inve in nurectic.
LAST-MODIFIED:20180722T051201Z
LOCATION:Coast Rd\, Barrytown\, New Zealand
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Tuesday Morning Extra Info
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
DTSTART:20180717T220000Z
DTEND:20180717T223000Z
DTSTAMP:20180722T060025Z
UID:3gqued55jui7omavqfr30civqp@google.com
CREATED:20180722T050847Z
DESCRIPTION:
LAST-MODIFIED:20180722T055756Z
LOCATION:Pariroa Beach
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Little Wednesday
TRANSP:OPAQUE
END:VEVENT
BEGIN:VEVENT
DTSTART:20180723T190000Z
DTEND:20180723T200000Z
DTSTAMP:20180722T060025Z
UID:1tqm6t508anprpeckn3rlndg6b@google.com
CREATED:20180722T055954Z
DESCRIPTION:
LAST-MODIFIED:20180722T055954Z
LOCATION:
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Conference Call
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].level, messages.SUCCESS)
        self.assertEqual(msgs[0].message, "5 iCal events loaded")
        events = getAllEvents(request, home=self.calendar)
        self.assertEqual(len(events), 5)
        tueMorn, daysOff, lilWeds, cnfCall, bigThur = events

        self.assertEqual(tueMorn.owner,      self.user)
        self.assertEqual(tueMorn.slug,       "tuesday-mornings")
        self.assertEqual(tueMorn.title,      "Tuesday Mornings")
        self.assertEqual(tueMorn.details,    "\n".join(["",
            "Fammulturacha matent theaminerviencess atinjuse it shin sue of "
            "Aothips to ming an sed prage thnisithass invernships oftegruct "
            "and encome. Taimen in grose to to ner grough ingin orgagences' "
            "of Fries seed", "",
            "Fritherovere Houps of custims analienessuppol. Tiriendindnew, "
            "vality a gruccouser to be the juse Truch ince lity Te "
            "therneramparcialues the the neshiplands tortandamength,  "
            "Comene ups a mitioney dend peachassfy de are to entices meand "
            "evelas of Friscerple th iseek arces a wind."]))
        self.assertEqual(tueMorn.tz.zone,    "Pacific/Auckland")
        self.assertEqual(tueMorn.time_from,  dt.time(9,30))
        self.assertEqual(tueMorn.time_to,    dt.time(11,30))
        self.assertEqual(tueMorn.location,   "Coast Rd, Barrytown, New Zealand")
        self.assertEqual(tueMorn.when,
            "Tuesdays (until 28 August 2018) at 9:30am to 11:30am")

        tueExceptions = tueMorn.get_children()
        self.assertEqual(len(tueExceptions), 3)
        tue24th, tue31st, tue14th = [page.specific for page in tueExceptions]

        self.assertEqual(tue24th.owner,      self.user)
        self.assertEqual(tue24th.overrides,  tueMorn)
        self.assertEqual(tue24th.slug,       "2018-07-24-postponement")
        self.assertEqual(tue24th.title,      "Postponement for Tuesday 24th of July")
        self.assertEqual(tue24th.details,    tueMorn.details)
        self.assertEqual(tue24th.tz.zone,    "Pacific/Auckland")
        self.assertEqual(tue24th.except_date,dt.date(2018,7,24))
        self.assertEqual(tue24th.date,       dt.date(2018,7,25))
        self.assertEqual(tue24th.time_from,  dt.time(9,30))
        self.assertEqual(tue24th.time_to,    dt.time(11,30))
        self.assertEqual(tue24th.location,   "Coast Rd, Barrytown, New Zealand")

        self.assertEqual(tue31st.owner,      self.user)
        self.assertEqual(tue31st.overrides,  tueMorn)
        self.assertEqual(tue31st.slug,       "2018-07-31-extra-info")
        self.assertEqual(tue31st.title,      "Extra-Info for Tuesday 31st of July")
        self.assertEqual(tue31st.extra_title,"Tuesday Morning Extra Info")
        self.assertEqual(tue31st.extra_information, "\n".join(["",
            "Extra Famin fork, andivery,  Hough in the re of re whels "
            "otedshiplue porturat inve in nurectic."]))
        self.assertEqual(tue31st.tz.zone,    "Pacific/Auckland")
        self.assertEqual(tue31st.except_date,dt.date(2018,7,31))

        self.assertEqual(tue14th.owner,      self.user)
        self.assertEqual(tue14th.overrides,  tueMorn)
        self.assertEqual(tue14th.slug,       "2018-08-14-cancellation")
        self.assertEqual(tue14th.title,      "Cancellation for Tuesday 14th of August")
        self.assertEqual(tue14th.cancellation_title,   "")
        self.assertEqual(tue14th.cancellation_details, "")
        self.assertEqual(tue14th.tz.zone,    "Pacific/Auckland")
        self.assertEqual(tue14th.except_date,dt.date(2018,8,14))

        self.assertEqual(daysOff.owner,      self.user)
        self.assertEqual(daysOff.slug,       "three-days-off")
        self.assertEqual(daysOff.title,      "Three days off")
        self.assertEqual(daysOff.details,    "")
        self.assertEqual(daysOff.tz.zone,    "Pacific/Auckland")
        self.assertEqual(daysOff.date_from,  dt.date(2018,7,13))
        self.assertEqual(daysOff.time_from,  None)
        self.assertEqual(daysOff.date_to,    dt.date(2018,7,15))
        self.assertEqual(daysOff.time_to,    None)
        self.assertEqual(daysOff.location,   "Home")

        self.assertEqual(lilWeds.owner,      self.user)
        self.assertEqual(lilWeds.slug,       "little-wednesday")
        self.assertEqual(lilWeds.title,      "Little Wednesday")
        self.assertEqual(lilWeds.details,    "")
        self.assertEqual(lilWeds.tz,         pytz.utc)
        self.assertEqual(lilWeds.date,       dt.date(2018,7,17))
        self.assertEqual(lilWeds.time_from,  dt.time(22))
        self.assertEqual(lilWeds.time_to,    dt.time(22,30))
        self.assertEqual(lilWeds.location,   "Pariroa Beach")
        self.assertEqual(lilWeds.when,       "Wednesday 18th of July at 10am to 10:30am")

        self.assertEqual(cnfCall.owner,      self.user)
        self.assertEqual(cnfCall.slug,       "conference-call")
        self.assertEqual(cnfCall.title,      "Conference Call")
        self.assertEqual(cnfCall.details,    "")
        self.assertEqual(cnfCall.tz,         pytz.utc)
        self.assertEqual(cnfCall.date,       dt.date(2018,7,23))
        self.assertEqual(cnfCall.time_from,  dt.time(19))
        self.assertEqual(cnfCall.time_to,    dt.time(20))

        self.assertEqual(bigThur.owner,      self.user)
        self.assertEqual(bigThur.slug,       "big-thursday")
        self.assertEqual(bigThur.title,      "Big Thursday")
        self.assertEqual(bigThur.details,
            "Hounit <b>catlike</b> at ethatial to thin a usistiques onshiend "
            "alits mily tente duse prommuniss ind sedships itommunte of perpollood.")
        self.assertEqual(bigThur.tz,         pytz.utc)
        self.assertEqual(bigThur.date_from,  dt.date(2018,7,25))
        self.assertEqual(bigThur.time_from,  dt.time(21))
        self.assertEqual(bigThur.date_to,    dt.date(2018,7,26))
        self.assertEqual(bigThur.time_to,    dt.time(8,30))
        self.assertEqual(bigThur.when,       "Thursday 26th of July at 9am to 8:30pm")

    @freeze_time("2018-02-01")
    @timezone.override("Pacific/Auckland")
    def testUtc2Local(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Test Data
X-WR-TIMEZONE:Australia/Sydney
X-WR-CALDESC:Sample data for Joyous test_ical unittest
BEGIN:VEVENT
DTSTART:20180725T210000Z
DTEND:20180726T083000Z
DTSTAMP:20180722T060025Z
UID:1uas8vo82gvhtn8jpr9nlnrmfk@google.com
CREATED:20180722T035919Z
DESCRIPTION:Hounit <b>catlike</b> at ethatial to thin a usistiques onshiend
  alits mily tente duse prommuniss ind sedships itommunte of perpollood.
LAST-MODIFIED:20180722T035919Z
LOCATION:
SEQUENCE:0
STATUS:CONFIRMED
SUMMARY:Big Thursday
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR
""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream, utc2local=True)
        events = getAllEvents(request, home=self.calendar)
        self.assertEqual(len(events), 1)
        bigThur = events[0]
        self.assertEqual(bigThur.owner,      self.user)
        self.assertEqual(bigThur.slug,       "big-thursday")
        self.assertEqual(bigThur.title,      "Big Thursday")
        self.assertEqual(bigThur.details,
            "Hounit <b>catlike</b> at ethatial to thin a usistiques onshiend "
            "alits mily tente duse prommuniss ind sedships itommunte of perpollood.")
        self.assertEqual(bigThur.tz.zone,    "Australia/Sydney")
        self.assertEqual(bigThur.date_from,  dt.date(2018,7,26))
        self.assertEqual(bigThur.time_from,  dt.time(7))
        self.assertEqual(bigThur.date_to,    dt.date(2018,7,26))
        self.assertEqual(bigThur.time_to,    dt.time(18,30))
        self.assertEqual(bigThur.when,       "Thursday 26th of July at 9am to 8:30pm")

    def testZipFile(self):
        path = "{}/djm@software.net.nz.ical.zip".format(settings.TEST_IMPORT_DIR)
        stream = open(path, "rb")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].level, messages.SUCCESS)
        self.assertEqual(msgs[0].message, "2 iCal events loaded")

    def testBadZipFile(self):
        path = "{}/junk.zip".format(settings.TEST_IMPORT_DIR)
        stream = open(path, "rb")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].level, messages.ERROR)
        self.assertEqual(msgs[0].message, "Could not parse iCalendar file "+path)

    def testZippedInvalidFile(self):
        path = "{}/foobar.ical.zip".format(settings.TEST_IMPORT_DIR)
        stream = open(path, "rb")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 2)
        self.assertEqual(msgs[0].level, messages.ERROR)
        self.assertEqual(msgs[0].message,
                         "Could not parse iCalendar file foobar@group.calendar.google.com.ics")
        self.assertEqual(msgs[1].level, messages.SUCCESS)
        self.assertEqual(msgs[1].message, "1 iCal events loaded")

    def testOutlook(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
PRODID:-//Microsoft Corporation//Outlook 11.0 MIMEDIR//EN
VERSION:2.0
METHOD:PUBLISH
BEGIN:VEVENT
DTSTART:20180730T092500
DTEND:20180730T101500
UID:7N7Y7V6J4N2U4I3U7H0N7W5O4V2U0K3H2E4Q4O7A2H0W1A5M6N
DTSTAMP:20180728T035656
DESCRIPTION;ENCODING=QUOTED-PRINTABLE:Booking number 9876543=0D=0A=0D=0AYour outgoing route is Westport > Wellington.=0D=0AThis route departs Westport on 30/Jul/2018 09:25 and arrives at Wellington at 10:15. The check-in time is 08:55.=0A
SUMMARY;ENCODING=QUOTED-PRINTABLE:Sounds Air - Flight Reminder
PRIORITY:3
BEGIN:VALARM
TRIGGER:-PT24H
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR
BEGIN:VCALENDAR
PRODID:-//Microsoft Corporation//Outlook 11.0 MIMEDIR//EN
VERSION:2.0
METHOD:PUBLISH
BEGIN:VEVENT
DTSTART:20180731T081500
DTEND:20180731T090000
UID:1G0K0V7K4L0H4Q4T5F4R8U2E0D0S4H2M6O1J6M5C5S2R4D0S2Q
DTSTAMP:20180728T035656
DESCRIPTION;ENCODING=QUOTED-PRINTABLE:Booking number 9876543=0D=0A=0D=0A=0D=0AYour return route is Wellington > Westport.=0D=0AThis route departs Wellington on 31/Jul/2018 08:15 and arrives at Westport at 09:00. The check-in time is 07:45.=0A
SUMMARY;ENCODING=QUOTED-PRINTABLE:Sounds Air - Flight Reminder
PRIORITY:3
BEGIN:VALARM
TRIGGER:-PT24H
ACTION:DISPLAY
DESCRIPTION:Reminder
END:VALARM
END:VEVENT
END:VCALENDAR
""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        events = [page.specific for page in self.calendar.get_children()]
        self.assertEqual(len(events), 2)
        flight1, flight2 = events

        self.assertEqual(flight1.slug,       "sounds-air-flight-reminder")
        self.assertEqual(flight1.title,      "Sounds Air - Flight Reminder")
        self.assertEqual(flight1.details,    "\r\n".join(["Booking number 9876543",
            "", "Your outgoing route is Westport > Wellington.",
            "This route departs Westport on 30/Jul/2018 09:25 and arrives at "
            "Wellington at 10:15. The check-in time is 08:55.\n"]))
        self.assertEqual(flight1.tz.zone,    "Asia/Tokyo")
        self.assertEqual(flight1.date,       dt.date(2018,7,30))
        self.assertEqual(flight1.time_from,  dt.time(9,25))
        self.assertEqual(flight1.time_to,    dt.time(10,15))

        self.assertEqual(flight2.slug,       "sounds-air-flight-reminder-2")
        self.assertEqual(flight2.title,      "Sounds Air - Flight Reminder")
        self.assertEqual(flight2.details,    "\r\n".join(["Booking number 9876543",
            "", "", "Your return route is Wellington > Westport.",
            "This route departs Wellington on 31/Jul/2018 08:15 and arrives at "
            "Westport at 09:00. The check-in time is 07:45.\n"]))
        self.assertEqual(flight2.tz.zone,    "Asia/Tokyo")
        self.assertEqual(flight2.date,       dt.date(2018,7,31))
        self.assertEqual(flight2.time_from,  dt.time(8,15))
        self.assertEqual(flight2.time_to,    dt.time(9))

    def testFacebook(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
PRODID:-//Facebook//NONSGML Facebook Events V1.0//EN
X-PUBLISHED-TTL:PT12H
X-ORIGINAL-URL:https://www.facebook.com/events/501511573641525/
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
DTSTAMP:20180729T102010Z
LAST-MODIFIED:20180729T102010Z
CREATED:20180729T102010Z
SEQUENCE:0
ORGANIZER;CN=Jjjj Bbbbb:MAILTO:noreply@facebookmail.com
ATTENDEE;CN=Bbbbb Wwwwww;PARTSTAT=ACCEPTED:https://www.facebook.com/bbwwwwww
ATTENDEE;CN=Jjjj Bbbbb;PARTSTAT=ACCEPTED:https://www.facebook.com/jjjj.bbbbb
ATTENDEE;CN=Pppp Tttttt;PARTSTAT=TENTATIVE:https://www.facebook.com/pppp.tttttt.123
DTSTART:20180831T070000Z
DTEND:20180831T100000Z
UID:e501511573641525@facebook.com
SUMMARY:Photo Comp - Prize Giving
LOCATION:TBC
URL:https://www.facebook.com/events/501511573641525/
DESCRIPTION:The much anticipated 2018 West Coa
 st Alpine Club is open!\nEntries cl
 ose midnight Friday 24th August. F
 ull details and entry form in the 
 linked PDF: https://www.dropbox.co
 m/s/5vxnep33ccxok9z/PhotoCompDetai
 ls.pdf?dl=0\nDetails of the prize g
 iving will be added here in due co
 urse\, but save the date in the mea
 n time.\n\nhttps://www.facebook.com/
 events/501511573641525/
CLASS:PUBLIC
STATUS:CONFIRMED
PARTSTAT:NEEDS-ACTION
END:VEVENT
END:VCALENDAR
""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        events = self.calendar.get_children()
        self.assertEqual(len(events), 1)
        event = events[0].specific

        self.assertEqual(event.slug,       "photo-comp-prize-giving")
        self.assertEqual(event.title,      "Photo Comp - Prize Giving")
        self.assertEqual(event.details,    "\n".join([
            "The much anticipated 2018 West Coast Alpine Club is open!",
            "Entries close midnight Friday 24th August. Full details and "
            "entry form in the linked PDF: https://www.dropbox.com/s/"
            "5vxnep33ccxok9z/PhotoCompDetails.pdf?dl=0",
            "Details of the prize giving will be added here in due course, "
            "but save the date in the mean time.", "",
            "https://www.facebook.com/events/501511573641525/"]))
        self.assertEqual(event.tz.zone,    "UTC")
        self.assertEqual(event.date,       dt.date(2018,8,31))
        self.assertEqual(event.time_from,  dt.time(7))
        self.assertEqual(event.time_to,    dt.time(10))

    def testUntilTZ(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
PRODID:-//Google Inc//Google Calendar 70.9054//EN
VERSION:2.0
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:djm6809@gmail.com
X-WR-TIMEZONE:Pacific/Auckland
BEGIN:VTIMEZONE
TZID:America/New_York
X-LIC-LOCATION:America/New_York
BEGIN:DAYLIGHT
TZOFFSETFROM:-0500
TZOFFSETTO:-0400
TZNAME:EDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0400
TZOFFSETTO:-0500
TZNAME:EST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20310101T050000
DTEND;TZID=America/New_York:20310101T070000
RRULE:FREQ=DAILY;UNTIL=20310108T045959Z
DTSTAMP:20190331T203301Z
UID:566vrur2ldqkvardnrb6tfrbdu@google.com
CREATED:20190331T200304Z
DESCRIPTION:New Year resolution
LAST-MODIFIED:20190331T203219Z
LOCATION:New York\, NY\, USA
SEQUENCE:5
STATUS:CONFIRMED
SUMMARY:Exercise
TRANSP:OPAQUE
END:VEVENT
END:VCALENDAR""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        events = self.calendar.get_children()
        self.assertEqual(len(events), 1)
        event = events[0].specific

        self.assertIs(type(event),         RecurringEventPage)
        self.assertEqual(event.slug,       "exercise")
        self.assertEqual(event.tz.zone,    "America/New_York")
        self.assertEqual(event.time_from,  dt.time(5))
        self.assertEqual(event.time_to,    dt.time(7))
        self.assertEqual(event.repeat.getCount(), 7)
        self.assertTrue(event._occursOn(dt.date(2031,1,1)))
        self.assertFalse(event._occursOn(dt.date(2031,1,8)))

    def testMultidayRecurringEvent(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//linuxsoftware.nz//NONSGML Joyous v0.8//EN
BEGIN:VEVENT
SUMMARY:Bought from a Rubber Man
DTSTART;TZID=Pacific/Auckland:20190402T160000
DTEND;TZID=Pacific/Auckland:20190404T180000
DTSTAMP:20190405T054311Z
UID:e6936872-f15c-4c47-92f2-3559a6610c78
SEQUENCE:1
RRULE:FREQ=WEEKLY;BYDAY=TU;WKST=SU
CREATED:20190405T054255Z
DESCRIPTION:<p></p>
LAST-MODIFIED:20190405T054255Z
LOCATION:
URL:http://localhost/calendar/bought-rubber-man/
END:VEVENT
BEGIN:VTIMEZONE
TZID:Pacific/Auckland
BEGIN:DAYLIGHT
DTSTART;VALUE=DATE-TIME:20180930T030000
RDATE:20190929T030000,20200927T030000,20210926T030000,20220925T030000,2023
 0924T030000,20240929T030000,20250928T030000,20260927T030000,20270926T03000
 0,20280924T030000,20290930T030000,20300929T030000,20310928T030000,20320926
 T030000,20330925T030000,20340924T030000,20350930T030000,20360928T030000,20
 370927T030000
TZNAME:NZDT
TZOFFSETFROM:+1200
TZOFFSETTO:+1300
END:DAYLIGHT
BEGIN:STANDARD
DTSTART;VALUE=DATE-TIME:20190407T020000
RDATE:20200405T020000,20210404T020000,20220403T020000,20230402T020000,2024
 0407T020000,20250406T020000,20260405T020000,20270404T020000,20280402T02000
 0,20290401T020000,20300407T020000,20310406T020000,20320404T020000,20330403
 T020000,20340402T020000,20350401T020000,20360406T020000,20370405T020000
TZNAME:NZST
TZOFFSETFROM:+1300
TZOFFSETTO:+1200
END:STANDARD
END:VTIMEZONE
END:VCALENDAR""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        events = self.calendar.get_children()
        self.assertEqual(len(events), 1)
        event = events[0].specific

        self.assertIs(type(event),         MultidayRecurringEventPage)
        self.assertEqual(event.title,      "Bought from a Rubber Man")
        self.assertEqual(event.tz.zone,    "Pacific/Auckland")
        self.assertEqual(event.num_days,   3)
        self.assertEqual(event.time_from,  dt.time(16))
        self.assertEqual(event.time_to,    dt.time(18))

    def testMultidayRescheduleEvent(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//linuxsoftware.nz//NONSGML Joyous v0.9//EN
BEGIN:VTIMEZONE
TZID:Pacific/Auckland
BEGIN:STANDARD
DTSTART;VALUE=DATE-TIME:20200405T020000
RDATE:20210404T020000,20220403T020000,20230402T020000,20240407T020000,2025
 0406T020000,20260405T020000,20270404T020000,20280402T020000,20290401T02000
 0,20300407T020000,20310406T020000,20320404T020000,20330403T020000,20340402
 T020000,20350401T020000,20360406T020000,20370405T020000
TZNAME:NZST
TZOFFSETFROM:+1300
TZOFFSETTO:+1200
END:STANDARD
BEGIN:DAYLIGHT
DTSTART;VALUE=DATE-TIME:20190929T030000
RDATE:20200927T030000,20210926T030000,20220925T030000,20230924T030000,2024
 0929T030000,20250928T030000,20260927T030000,20270926T030000,20280924T03000
 0,20290930T030000,20300929T030000,20310928T030000,20320926T030000,20330925
 T030000,20340924T030000,20350930T030000,20360928T030000,20370927T030000
TZNAME:NZDT
TZOFFSETFROM:+1200
TZOFFSETTO:+1300
END:DAYLIGHT
END:VTIMEZONE
BEGIN:VEVENT
SUMMARY:Colour In
DTSTART;TZID=Pacific/Auckland:20200101T103000
DTEND;TZID=Pacific/Auckland:20200102T140000
DTSTAMP:20200101T012156Z
UID:6ca93786-722e-410c-91a2-bc8a6ecdadb9
SEQUENCE:1
RRULE:FREQ=WEEKLY;BYDAY=WE;WKST=SU
CREATED:20200101T011254Z
DESCRIPTION:Paint that scene.
X-ALT-DESC;FMTTYPE=text/html:<h2>Paint that scene.</h2>
LAST-MODIFIED:20200101T011254Z
LOCATION:
URL:http://localhost/calendar/colour/
END:VEVENT
BEGIN:VEVENT
SUMMARY:Knock
DTSTART;TZID=Pacific/Auckland:20200108T110000
DTEND;TZID=Pacific/Auckland:20200109T140000
DTSTAMP:20200101T012156Z
UID:6ca93786-722e-410c-91a2-bc8a6ecdadb9
RECURRENCE-ID;TZID=Pacific/Auckland:20200108T103000
SEQUENCE:1
CREATED:20200101T011852Z
DESCRIPTION:
LAST-MODIFIED:20200101T011852Z
LOCATION:
URL:http://localhost/calendar/colour/2020-01-08-postponement/
END:VEVENT
BEGIN:VEVENT
SUMMARY:Change
DTSTART;TZID=Pacific/Auckland:20200116T110000
DTEND;TZID=Pacific/Auckland:20200116T143000
DTSTAMP:20200101T012156Z
UID:6ca93786-722e-410c-91a2-bc8a6ecdadb9
RECURRENCE-ID;TZID=Pacific/Auckland:20200115T103000
SEQUENCE:1
CREATED:20200101T012044Z
DESCRIPTION:
LAST-MODIFIED:20200101T012044Z
LOCATION:
URL:http://localhost/calendar/colour/2020-01-15-postponement/
END:VEVENT
END:VCALENDAR""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        events = self.calendar.get_children()
        self.assertEqual(len(events), 1)
        event = events[0].specific
        self.assertIs(type(event),          MultidayRecurringEventPage)
        self.assertEqual(event.title,       "Colour In")
        self.assertEqual(event.details,     "<h2>Paint that scene.</h2>")
        self.assertEqual(event.tz.zone,     "Pacific/Auckland")
        self.assertEqual(event.num_days,    2)
        self.assertEqual(event.time_from,   dt.time(10,30))
        self.assertEqual(event.time_to,     dt.time(14))
        exceptions = event.get_children()
        self.assertEqual(len(exceptions),   2)
        resched = exceptions[0].specific
        self.assertIs(type(resched),        RescheduleMultidayEventPage)
        self.assertEqual(resched.postponement_title, "Knock")
        self.assertEqual(resched.num_days,  2)
        self.assertEqual(resched.time_from, dt.time(11))
        self.assertEqual(resched.time_to,   dt.time(14))
        resched = exceptions[1].specific
        self.assertIs(type(resched),        RescheduleMultidayEventPage)
        self.assertEqual(resched.postponement_title, "Change")
        self.assertEqual(resched.num_days,  1)
        self.assertEqual(resched.time_from, dt.time(11))
        self.assertEqual(resched.time_to,   dt.time(14,30))

    def testLoadInvalidFile(self):
        stream = BytesIO(rb"""FOO:BAR:SNAFU""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg.level, messages.ERROR)
        self.assertEqual(msg.message, "Could not parse iCalendar file ")

    def testLoadEventMissingUID(self):
        stream = BytesIO(rb"""
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Bloor &amp; Spadina - ECPv4.6.13//NONSGML v1.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Bloor &amp; Spadina
X-ORIGINAL-URL:http://bloorneighbours.ca
X-WR-CALDESC:Events for Bloor &amp; Spadina
BEGIN:VEVENT
DTSTART;TZID=UTC+0:20180407T093000
DTEND;TZID=UTC+0:20180407T113000
DTSTAMP:20180402T054745
CREATED:20180304T225154Z
LAST-MODIFIED:20180304T225154Z
SUMMARY:Mini-Fair & Garage Sale
DESCRIPTION:
URL:http://bloorneighbours.ca/event/mini-fair-garage-sale/
END:VEVENT
END:VCALENDAR""")
        request = self._getRequest()
        self.handler.load(self.calendar, request, stream)
        events = SimpleEventPage.events.child_of(self.calendar)            \
                                       .filter(date=dt.date(2018,4,7)).all()
        self.assertEqual(len(events), 0)
        msgs = list(messages.get_messages(request))
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertEqual(msg.level, messages.ERROR)
        self.assertEqual(msg.message, "Could not load 1 iCal events")

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
        self.handler = ICalHandler()

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
        self.assertEqual(response.get('Content-Type'), "text/calendar")
        self.assertEqual(response.get('Content-Disposition'),
                         "attachment; filename=events.ics")
        self.assertEqual(response.content.count(b"BEGIN:VEVENT"), 2)

    def testServeEvent(self):
        response = self.handler.serve(self.dicerun,
                                      self._getRequest("/events/mercy-dice-run/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), "text/calendar")
        self.assertEqual(response.get('Content-Disposition'),
                         "attachment; filename=mercy-dice-run.ics")
        self.assertEqual(response.content.count(b"BEGIN:VEVENT"), 1)
        self.assertIn(b"SUMMARY:Mercy Dice Run", response.content)
        self.assertIn(b"DTSTART;TZID=Asia/Tokyo:20200316T000000", response.content)
        self.assertIn(b"DTEND;TZID=Asia/Tokyo:20200316T235959", response.content)
        self.assertIn(b"LOCATION:Newtown", response.content)
        self.assertIn(b"URL:http://joy.test/events/mercy-dice-run", response.content)

    def testServePage(self):
        response = self.handler.serve(self.home, self._getRequest("/"))
        self.assertIsNone(response)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
