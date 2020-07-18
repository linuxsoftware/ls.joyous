# ------------------------------------------------------------------------------
# Test Holidays
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from unittest.mock import Mock
from django.conf import settings
from django.test import TestCase, override_settings
from holidays import NZ, AU
from ls.joyous.models import CalendarPage
from ls.joyous.models import SimpleEventPage
from ls.joyous.holidays import Holidays
from ls.joyous.holidays.parser import parseHolidays, _parseSubdivisions
from .testutils import freeze_timetz, getPage

# ------------------------------------------------------------------------------
class TestHolidays(TestCase):
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

    @override_settings(JOYOUS_HOLIDAYS = None)
    def testNoNames(self):
        hols = Holidays()
        self.assertEqual(hols.names(), [])

    @freeze_timetz("2017-05-31")
    def testNZNames(self):
        hols = Holidays()
        self.assertEqual(hols.names(), [
                         "New Year's Day",
                         "Day after New Year's Day",
                         "New Year's Day (Observed)",
                         "Day after New Year's Day (Observed)",
                         'Wellington Anniversary Day',
                         'Auckland Anniversary Day',
                         'Nelson Anniversary Day',
                         'Waitangi Day',
                         'Waitangi Day (Observed)',
                         'Taranaki Anniversary Day',
                         'Otago Anniversary Day',
                         'Good Friday',
                         'Easter Monday',
                         'Southland Anniversary Day',
                         'Anzac Day',
                         'Anzac Day (Observed)',
                         "Queen's Birthday",
                         'South Canterbury Anniversary Day',
                         "Hawke's Bay Anniversary Day",
                         'Labour Day',
                         'Marlborough Anniversary Day',
                         'Canterbury Anniversary Day',
                         'Chatham Islands Anniversary Day',
                         'Westland Anniversary Day',
                         'Christmas Day',
                         'Boxing Day',
                         'Christmas Day (Observed)',
                         'Boxing Day (Observed)'])

    @override_settings(JOYOUS_HOLIDAYS = None)
    def testSimpleNames(self):
        hols = Holidays()
        hols.add(dt.date(2021,4,29), "HAPPY HAPPY")
        self.assertEqual(hols.names(), ["HAPPY HAPPY"])

    @override_settings(JOYOUS_HOLIDAYS = None)
    def testWorkalendarNames(self):
        class Woral:
            get_calendar_holidays = Mock(return_value=[(dt.date(1999,4,30),
                                                        "JOY JOY")])
        woral = Woral()
        hols = Holidays()
        hols.register(woral)
        self.assertEqual(hols.names(), ["JOY JOY"])

    def testAdd(self):
        ausHols = Holidays(None)
        ausHols.add(dt.date(2020,10,20), "Kangaroo Day")
        ausHols.register(AU())
        nzHols  = Holidays(None)
        nzHols.add(dt.date(2020,10,20), "Kiwi Day")
        nzHols.register(NZ())
        tasHols = ausHols + nzHols
        self.assertEqual(tasHols.get(dt.date(2020,10,20)),
                         "Kangaroo Day, Kiwi Day")
        self.assertEqual(len(tasHols.srcs), 3)
        self.assertIs(type(tasHols.srcs[0]), dict)
        self.assertIs(type(tasHols.srcs[1]), AU)
        self.assertIs(type(tasHols.srcs[2]), NZ)
        self.assertEqual(tasHols.names(), [
                         "New Year's Day",
                         "Day after New Year's Day",
                         "New Year's Day (Observed)",
                         "Day after New Year's Day (Observed)",
                         'Australia Day',
                         'Australia Day (Observed)',
                         'Waitangi Day',
                         'Waitangi Day (Observed)',
                         'Good Friday',
                         'Easter Monday',
                         'Anzac Day',
                         'Anzac Day (Observed)',
                         "Queen's Birthday",
                         'Kangaroo Day',
                         'Kiwi Day',
                         'Labour Day',
                         'Christmas Day',
                         'Boxing Day',
                         'Christmas Day (Observed)',
                         'Boxing Day (Observed)'])

# ------------------------------------------------------------------------------
class TestParser(TestCase):
    def testScotland(self):
        hols = parseHolidays("Scotland")
        self.assertEqual(hols.get(dt.date(2019,11,30)), "St. Andrew's Day")

    def testAllCountries(self):
        from ls.joyous.holidays.parser import _PYTHON_HOLIDAYS_MAP
        hols = parseHolidays("*")
        classes = [hol.__class__ for hol in hols.holidays if hol.country]
        self.assertCountEqual(classes, _PYTHON_HOLIDAYS_MAP.values())

    def testCountriesNE(self):
        hols = parseHolidays("*[NE]")
        self.assertEqual(hols.get(dt.date(2019,3,1)),
                         "Jahrestag der Ausrufung der Republik")
        self.assertEqual(hols.get(dt.date(2019,4,26)),
                         "Arbor Day")

    def testNorthIsland(self):
        hols = parseHolidays("NZ[NTL,AUK,HKB,TKI,WGN]")
        self.assertEqual(hols.get(dt.date(2020,1,20)),
                         "Wellington Anniversary Day")
        self.assertEqual(hols.get(dt.date(2020,1,27)),
                         "Auckland Anniversary Day")
        self.assertEqual(hols.get(dt.date(2020,3,9)),
                         "Taranaki Anniversary Day")
        self.assertEqual(hols.get(dt.date(2020,10,23)),
                         "Hawke's Bay Anniversary Day")

    def testInvalidCountry(self):
        self.assertIsNone(parseHolidays("Ruritania"))

    def testInvalidSubdivision(self):
        from holidays import UK
        self.assertEqual(_parseSubdivisions("ZZZ", UK), 0)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
