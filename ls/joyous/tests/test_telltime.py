# ------------------------------------------------------------------------------
# Test Telltime Utilities
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.test import TestCase
from .testutils import datetimetz
from ls.joyous.utils.telltime import (getAwareDatetime, getLocalDatetime,
        getLocalDateAndTime, getLocalDate, getLocalTime,
        timeFrom, timeTo, timeFormat, dateFormat, dateFormatDMY)

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


class TestNullableTimes(TestCase):
    def testTimeFrom(self):
        self.assertEqual(timeFrom(None), dt.time(0))
        self.assertEqual(timeFrom(dt.time(8)), dt.time(8))

    def testTimeTo(self):
        self.assertEqual(timeTo(None), dt.time.max)
        self.assertEqual(timeTo(dt.time(8)), dt.time(8))


class TestFormats(TestCase):
    def testTimeFormat(self):
        self.assertEqual(timeFormat(None), "")
        self.assertEqual(timeFormat("","","Aaa","Bbb"), "")
        self.assertEqual(timeFormat(dt.time(13,26)), "1:26pm")
        self.assertEqual(timeFormat(dt.time(8), prefix="~~"), "~~8am")
        self.assertEqual(timeFormat(dt.time(8), dt.time(11)), "8am to 11am")
        self.assertEqual(timeFormat(dt.time(20), dt.time(2), "at ", "-> "),
                         "at 8pm -> 2am")

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

    def testDateFormatDMY(self):
        self.assertEqual(dateFormatDMY(dt.date(2016,5,22)), "22 May 2016")
        self.assertEqual(dateFormatDMY(None), "")


