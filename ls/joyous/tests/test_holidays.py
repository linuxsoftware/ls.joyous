# ------------------------------------------------------------------------------
# Test Holidays
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from unittest.mock import Mock
from django.conf import settings
from django.test import TestCase, override_settings
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import SimpleEventPage
from ls.joyous.holidays import Holidays
from .testutils import freeze_timetz, getPage


# ------------------------------------------------------------------------------
class Test(TestCase):
    @override_settings()
    def testNoSettings(self):
        del settings.JOYOUS_HOLIDAYS
        hols = Holidays()
        self.assertEqual(hols.simple, {})
        self.assertEqual(hols.srcs, [{}])
        self.assertEqual(hols.get(dt.date(1999,4,25)), "")

    def testNZSetting(self):
        hols = Holidays()
        self.assertEqual(hols.get(dt.date(1999,4,25)), "Anzac Day")

    @override_settings(JOYOUS_HOLIDAYS = None)
    def testSimple(self):
        hols = Holidays()
        hols.add(dt.date(1999,4,29), "HAPPY HAPPY")
        self.assertEqual(hols.get(dt.date(1999,4,29)), "HAPPY HAPPY")

    @override_settings(JOYOUS_HOLIDAYS = None)
    def testWorkalendar(self):
        class Woral:
            get_holiday_label = Mock(return_value="JOY JOY")
        woral = Woral()
        hols = Holidays()
        hols.register(woral)
        self.assertEqual(hols.srcs, [{}, woral])
        self.assertEqual(hols.get(dt.date(1999,4,30)), "JOY JOY")
        woral.get_holiday_label.assert_called_with(dt.date(1999,4,30))

    def testMultiHolidays(self):
        hols = Holidays()
        hols.add(dt.date(1999,1,1), "Gliffy")
        hols.add(dt.date(1999,1,1), "Whatnot")
        self.assertEqual(hols.get(dt.date(1999,1,1)),
                         "Gliffy, Whatnot, New Year's Day")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
