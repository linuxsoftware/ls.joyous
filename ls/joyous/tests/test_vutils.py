# ------------------------------------------------------------------------------
# Test ical utility clases
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from icalendar import vDatetime
from django.test import TestCase
from django.utils import timezone
from icalendar import vDatetime, vDate, vRecur, vDDDTypes, vText
from ls.joyous.utils.telltime import getLocalDatetime
from ls.joyous.formats.ical import (vDt, vSmart, TimeZoneSpan, VMatch,
                                    CalendarTypeError)
from freezegun import freeze_time

# ------------------------------------------------------------------------------
class TestVDt(TestCase):
    def testNone(self):
        v = vDt()
        self.assertFalse(v)
        self.assertEqual(v, None)
        self.assertEqual(v.date(), None)
        self.assertEqual(v.time(), None)
        self.assertEqual(v.datetime(), None)
        self.assertEqual(v.tzinfo(), None)
        self.assertEqual(v.zone(), None)
        self.assertEqual(v.timezone(), pytz.timezone("Asia/Tokyo"))

    def testNaiveDt(self):
        mo = dt.datetime(1987, 6, 21, 3, 54, 0)
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, vDatetime(mo))
        self.assertEqual(v, vDatetime.from_ical("19870621T035400"))
        self.assertEqual(v.date(), mo.date())
        self.assertEqual(v.time(), mo.time())
        self.assertEqual(v.datetime(), timezone.make_aware(mo))
        self.assertEqual(v.tzinfo(), None)
        self.assertEqual(v.zone(), None)
        self.assertEqual(v.timezone(), pytz.timezone("Asia/Tokyo"))

    def testTzinfoDt(self):
        mo = dt.datetime(2020, 2, 2, 2, tzinfo=dt.timezone.utc)
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, vDatetime(mo))
        self.assertEqual(v, vDatetime.from_ical("20200202T020000Z"))
        self.assertEqual(v.date(), mo.date())
        self.assertEqual(v.time(), mo.time())
        self.assertEqual(v.datetime(), mo)
        self.assertEqual(v.tzinfo(), mo.tzinfo)
        self.assertEqual(v.zone(), "UTC+00:00")
        self.assertEqual(v.timezone(), dt.timezone.utc)

    def testAwareDt(self):
        mo = vDatetime(timezone.make_aware(dt.datetime(2013, 4, 25, 6, 0),
                                           pytz.timezone("Pacific/Chatham")))
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, mo.dt)
        self.assertEqual(v, vDatetime.from_ical("20130425T060000",
                                                "Pacific/Chatham"))
        self.assertEqual(v.date(), mo.dt.date())
        self.assertEqual(v.time(), mo.dt.time())
        self.assertEqual(v.datetime(), mo.dt)
        self.assertEqual(v.tzinfo(), mo.dt.tzinfo)
        self.assertEqual(v.zone(), "Pacific/Chatham")
        self.assertEqual(v.timezone(), pytz.timezone("Pacific/Chatham"))

    def testUnknownTZDt(self):
        mo = timezone.make_aware(dt.datetime(2013, 4, 25, 6, 0))
        mo.tzinfo.zone = "Japan/Edo"
        v = vDt(mo)
        self.assertTrue(v)
        self.assertEqual(v, mo)
        self.assertEqual(v, vDatetime(mo))
        self.assertEqual(v.date(), mo.date())
        self.assertEqual(v.time(), mo.time())
        self.assertEqual(v.datetime(), mo)
        self.assertEqual(v.tzinfo(), mo.tzinfo)
        self.assertEqual(v.zone(), "Japan/Edo")
        with self.assertRaises(CalendarTypeError):
            v.timezone()

    def testDate(self):
        day = dt.date(1979, 8, 16)
        v = vDt(day)
        self.assertTrue(v)
        self.assertEqual(v, day)
        self.assertEqual(v, vDate(day))
        self.assertEqual(v, vDate.from_ical("19790816"))
        self.assertEqual(v.date(), day)
        self.assertEqual(v.time(), None)
        self.assertEqual(v.datetime(), getLocalDatetime(day, dt.time.min))
        self.assertEqual(v.tzinfo(), None)
        self.assertEqual(v.zone(), None)
        self.assertEqual(v.timezone(), pytz.timezone("Asia/Tokyo"))

    def testDateInc(self):
        day = dt.date(1979, 8, 16)
        v = vDt(day, inclusive=True)
        self.assertTrue(v)
        self.assertEqual(v, dt.date(1979, 8, 17))
        self.assertEqual(v.date(), dt.date(1979, 8, 17))
        self.assertEqual(v.date(inclusive=True), day)

# ------------------------------------------------------------------------------
class TestVSmart(TestCase):
    def testEmpty(self):
        v = vSmart("")
        self.assertFalse(v)
        self.assertEqual(str(v), "")

    def testStr(self):
        v = vSmart("ġedæġhwāmlīcan")
        self.assertTrue(v)
        self.assertEqual(str(v), "ġedæġhwāmlīcan")

    def testQuoPri(self):
        v = vSmart(b'=C4=A1ed=C3=A6=C4=A1hw=C4=81ml=C4=ABcan')
        v.params['ENCODING'] = "QUOTED-PRINTABLE"
        self.assertEqual(str(v), "ġedæġhwāmlīcan")

    def testBase64(self):
        v = vSmart(b'xKFlZMOmxKFod8SBbWzEq2Nhbg==')
        v.params['ENCODING'] = "BASE64"
        self.assertEqual(str(v), "ġedæġhwāmlīcan")

# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
