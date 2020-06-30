# ------------------------------------------------------------------------------
# Test Telltime Utilities
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.test import TestCase, override_settings
from django.utils import timezone
from .testutils import datetimetz
from ls.joyous.utils.telltime import (getAwareDatetime, getLocalDatetime,
        getLocalDateAndTime, getLocalDate, getLocalTime, getLocalTimeAtDate,
        getTimeFrom, getTimeTo, timeFormat, dateFormat, dateShortFormat)

# ------------------------------------------------------------------------------
class TestLocalTimes(TestCase):
    def testGetAwareDatetime(self):
        when = getAwareDatetime(dt.date(1999,12,1), dt.time(2),
                                pytz.timezone("Asia/Kuala_Lumpur"))
        self.assertEqual(when.tzinfo.zone, "Asia/Kuala_Lumpur")
        self.assertEqual(when.date(), dt.date(1999,12,1))
        self.assertEqual(when.time(), dt.time(2))
        when = getAwareDatetime(dt.date(2004,2,15), None,
                                pytz.timezone("Australia/Melbourne"))
        self.assertEqual(when.tzinfo.zone, "Australia/Melbourne")
        self.assertEqual(when.date(), dt.date(2004,2,15))
        self.assertEqual(when.time(), dt.time.max)

    def testGetLocalDatetime(self):
        self.assertEqual(getLocalDatetime(dt.date(2019,1,1), dt.time(1)),
                         datetimetz(2019,1,1,1))
        when = getLocalDatetime(dt.date(2003,9,2), dt.time(10,45,1),
                                pytz.timezone("Asia/Tokyo"))
        self.assertEqual(when, datetimetz(2003,9,2,10,45,1))
        when = getLocalDatetime(dt.date(2017,3,23), dt.time(18),
                                pytz.timezone("Europe/Prague"))
        self.assertEqual(when.tzinfo.zone, "Asia/Tokyo")
        self.assertEqual(when.date(), dt.date(2017,3,24))
        self.assertEqual(when.time(), dt.time(2)),
        when = getLocalDatetime(dt.date(2006,6,22), None,
                                pytz.timezone("America/Toronto"), dt.time(0))
        self.assertEqual(when.tzinfo.zone, "Asia/Tokyo")
        self.assertEqual(when.date(), dt.date(2006,6,22))
        self.assertEqual(when.time(), dt.time(0))

    def testGetLocalDateAndTime(self):
        date, time = getLocalDateAndTime(dt.date(1987,1,1), dt.time(1))
        self.assertEqual(date, dt.date(1987,1,1))
        localTZ = pytz.timezone("Asia/Tokyo")
        self.assertEqual(time, dt.time(1).replace(tzinfo=localTZ))
        date, time = getLocalDateAndTime(dt.date(2011,4,28), None,
                                pytz.timezone("Asia/Yerevan"))
        self.assertEqual(date, dt.date(2011,4,29))
        self.assertEqual(time, None)

    def testGetLocalDate(self):
        date = getLocalDate(dt.date(1993,8,8), None,
                            pytz.timezone("Europe/London"))
        self.assertEqual(date, dt.date(1993,8,9))

    def testGetLocalTime(self):
        time = getLocalTime(dt.date(2018,5,8), dt.time(22,44),
                            pytz.timezone("Pacific/Auckland"))
        localTZ = pytz.timezone("Asia/Tokyo")
        self.assertEqual(time, dt.time(19,44).replace(tzinfo=localTZ))

    def testGetLocalTimeAtDate(self):
        localTZ = pytz.timezone("Asia/Tokyo")
        time = getLocalTimeAtDate(dt.date(2018,5,8), dt.time(22,44),
                                  pytz.timezone("Pacific/Auckland"))
        self.assertEqual(time, dt.time(19,44).replace(tzinfo=localTZ))

    def testGetLocalTimeAtDateOffset1(self):
        localTZ = pytz.timezone("Asia/Tokyo")
        time = getLocalTimeAtDate(dt.date(2019,6,28), dt.time(8,10),
                                  pytz.timezone("America/Los_Angeles"))
        self.assertEqual(time, dt.time(0,10).replace(tzinfo=localTZ))

    @timezone.override("Pacific/Kiritimati")
    def testGetLocalTimeAtDateOffset2(self):
        localTZ = pytz.timezone("Pacific/Kiritimati")
        time = getLocalTimeAtDate(dt.date(2019,1,1), dt.time(23,30),
                                  pytz.timezone("Pacific/Pago_Pago"))
        self.assertEqual(time, dt.time(0,30).replace(tzinfo=localTZ))

# ------------------------------------------------------------------------------
class TestNullableTimes(TestCase):
    def testTimeFrom(self):
        self.assertEqual(getTimeFrom(None), dt.time(0))
        self.assertEqual(getTimeFrom(dt.time(8)), dt.time(8))

    def testTimeTo(self):
        self.assertEqual(getTimeTo(None), dt.time.max)
        self.assertEqual(getTimeTo(dt.time(8)), dt.time(8))

# ------------------------------------------------------------------------------
class TestFormats(TestCase):
    def testTimeFormat(self):
        self.assertEqual(timeFormat(None), "")
        self.assertEqual(timeFormat("","","Aaa","Bbb"), "")
        self.assertEqual(timeFormat(dt.time(13,26)), "1:26pm")
        self.assertEqual(timeFormat(dt.time(8), prefix="~~"), "~~8am")
        self.assertEqual(timeFormat(dt.time(8), dt.time(11)), "8am to 11am")
        self.assertEqual(timeFormat(dt.time(20), dt.time(2), "at ", "->"),
                         "at 8pm -> 2am")
        with override_settings(JOYOUS_TIME_FORMAT = None):
            self.assertEqual(timeFormat(dt.time(8)), "8 a.m.")
        with override_settings(JOYOUS_TIME_FORMAT = "Hi"):
            self.assertEqual(timeFormat(dt.time(8), dt.time(11)),
                             "0800 to 1100")

    def testDateFormat(self):
        self.assertEqual(dateFormat(None), "")
        self.assertEqual(dateFormat(dt.date(2017,2,16)),
                         "Thursday 16th of February 2017")
        today = dt.date.today()
        parts = dateFormat(today).split()
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0], "{:%A}".format(today))
        self.assertEqual(int(parts[1][:-2]), today.day)
        self.assertIn(parts[1][-2:], ["st", "nd", "rd", "th"])
        self.assertEqual(parts[2], "of")
        self.assertEqual(parts[3], "{:%B}".format(today))
        with override_settings(JOYOUS_DATE_FORMAT = None):
            self.assertEqual(dateFormat(dt.date(2017,2,16)),
                             "Feb. 16, 2017")
        with override_settings(JOYOUS_DATE_FORMAT = "ymd"):
            self.assertEqual(dateFormat(dt.date(2017,2,16)), "170216")

    def testDateShortFormat(self):
        self.assertEqual(dateShortFormat(dt.date(2016,5,22)), "22 May 2016")
        self.assertEqual(dateShortFormat(None), "")
        with override_settings(JOYOUS_DATE_SHORT_FORMAT = None):
            self.assertEqual(dateShortFormat(dt.date(2017,2,16)),
                             "02/16/2017")
        with override_settings(JOYOUS_DATE_SHORT_FORMAT = "M jS"):
            self.assertEqual(dateShortFormat(dt.date(2017,2,16)), "Feb 16th")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
