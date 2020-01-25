# ------------------------------------------------------------------------------
# Test Formatting weeks
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase, override_settings
import ls.joyous.utils.weeks
from ls.joyous.utils.weeks import (
        _iso_year_start, _iso_info, _iso_num_weeks,
        _gregorian_to_iso, _iso_to_gregorian, _iso_week_of_month)
from ls.joyous.utils.weeks import (
        _ssweek_year_start, _ssweek_info, _ssweek_num_weeks,
        _gregorian_to_ssweek, _ssweek_to_gregorian, _ssweek_of_month)
from django.utils.translation import override
from django.utils.formats import get_format
import importlib

# ------------------------------------------------------------------------------
class TestMondayStartingWeek(TestCase):
    def testYearStart(self):
        self.assertEqual(_iso_year_start(1991), dt.date(1990,12,31))
        self.assertEqual(_iso_year_start(2006), dt.date(2006,1,2))
        self.assertEqual(_iso_year_start(2020), dt.date(2019,12,30))
        self.assertEqual(_iso_year_start(2036), dt.date(2035,12,31))

    def testNumWeeksInYear(self):
        self.assertEqual(_iso_num_weeks(1991), 52)
        self.assertEqual(_iso_num_weeks(2006), 52)
        self.assertEqual(_iso_num_weeks(2020), 53)
        self.assertEqual(_iso_num_weeks(2036), 52)

    def testWeekOfMonth(self):
        self.assertEqual(_iso_week_of_month(dt.date(1990,5,31)),  4)
        self.assertEqual(_iso_week_of_month(dt.date(2005,1,2)),   0)
        self.assertEqual(_iso_week_of_month(dt.date(2021,12,13)), 2)
        self.assertEqual(_iso_week_of_month(dt.date(2030,10,8)),  1)

    def testGregorianToWeekDate(self):
        self.assertEqual(_gregorian_to_iso(dt.date(1991,5,25)),  (1991,21,6))
        self.assertEqual(_gregorian_to_iso(dt.date(2007,1,2)),   (2007,1,2))
        self.assertEqual(_gregorian_to_iso(dt.date(2022,12,13)), (2022,50,2))
        self.assertEqual(_gregorian_to_iso(dt.date(2035,12,31)), (2036,1,1))

    def testWeekToGregorianDate(self):
        self.assertEqual(_iso_to_gregorian(1990,2,6),  dt.date(1990,1,13))
        self.assertEqual(_iso_to_gregorian(2005,20,1), dt.date(2005,5,16))
        self.assertEqual(_iso_to_gregorian(2020,53,5), dt.date(2021,1,1))
        self.assertEqual(_iso_to_gregorian(2035,6,7),  dt.date(2035,2,11))

    def testWeekInfo(self):
        # (first_day, last_day, prev_year_num_weeks, year_num_weeks)
        self.assertEqual(_iso_info(1991,2),
                         (dt.date(1991,1,7),  dt.date(1991,1,13), 52, 52))
        self.assertEqual(_iso_info(2006,20),
                         (dt.date(2006,5,15), dt.date(2006,5,21), 52, 52))
        self.assertEqual(_iso_info(2020,40),
                         (dt.date(2020,9,28), dt.date(2020,10,4), 52, 53))
        self.assertEqual(_iso_info(2036,21),
                         (dt.date(2036,5,19), dt.date(2036,5,25), 52, 52))

# ------------------------------------------------------------------------------
class TestSundayStartingWeek(TestCase):
    def testYearStart(self):
        self.assertEqual(_ssweek_year_start(1991), dt.date(1990,12,30))
        self.assertEqual(_ssweek_year_start(2006), dt.date(2006,1,1))
        self.assertEqual(_ssweek_year_start(2020), dt.date(2019,12,29))
        self.assertEqual(_ssweek_year_start(2036), dt.date(2035,12,30))

    def testNumWeeksInYear(self):
        self.assertEqual(_ssweek_num_weeks(1991), 52)
        self.assertEqual(_ssweek_num_weeks(2006), 52)
        self.assertEqual(_ssweek_num_weeks(2020), 53)
        self.assertEqual(_ssweek_num_weeks(2036), 53)

    def testWeekOfMonth(self):
        self.assertEqual(_ssweek_of_month(dt.date(1990,5,31)),  4)
        self.assertEqual(_ssweek_of_month(dt.date(2005,1,2)),   1)
        self.assertEqual(_ssweek_of_month(dt.date(2021,12,13)), 2)
        self.assertEqual(_ssweek_of_month(dt.date(2030,10,8)),  1)

    def testGregorianToWeekDate(self):
        self.assertEqual(_gregorian_to_ssweek(dt.date(1991,5,25)),  (1991,21,6))
        self.assertEqual(_gregorian_to_ssweek(dt.date(2007,1,2)),   (2007,1,2))
        self.assertEqual(_gregorian_to_ssweek(dt.date(2022,12,13)), (2022,50,2))
        self.assertEqual(_gregorian_to_ssweek(dt.date(2035,12,31)), (2036,1,1))
        self.assertEqual(_gregorian_to_ssweek(dt.date(2019,12,1)),  (2019,49,7))
        self.assertEqual(_gregorian_to_ssweek(dt.date(2019,12,29)), (2020,1,7))

    def testWeekToGregorianDate(self):
        self.assertEqual(_ssweek_to_gregorian(1990,2,6),  dt.date(1990,1,12))
        self.assertEqual(_ssweek_to_gregorian(2005,20,1), dt.date(2005,5,15))
        self.assertEqual(_ssweek_to_gregorian(2020,53,5), dt.date(2020,12,31))
        self.assertEqual(_ssweek_to_gregorian(2035,6,7),  dt.date(2035,2,10))

    def testWeekInfo(self):
        # (first_day, last_day, prev_year_num_weeks, year_num_weeks)
        self.assertEqual(_ssweek_info(1991,2),
                         (dt.date(1991,1,6),  dt.date(1991,1,12), 52, 52))
        self.assertEqual(_ssweek_info(2006,20),
                         (dt.date(2006,5,14), dt.date(2006,5,20), 52, 52))
        self.assertEqual(_ssweek_info(2020,40),
                         (dt.date(2020,9,27), dt.date(2020,10,3), 52, 53))
        self.assertEqual(_ssweek_info(2036,21),
                         (dt.date(2036,5,18), dt.date(2036,5,24), 52, 53))

# ------------------------------------------------------------------------------
class TestSetting(TestCase):
    @override('en-gb')
    def testMondayStartingWeek(self):
        # FIRST_DAY_OF_WEEK is Monday for Great Britain
        self.assertEqual(get_format('FIRST_DAY_OF_WEEK'), 1)
        importlib.reload(ls.joyous.utils.weeks)
        from ls.joyous.utils.weeks import (week_info, num_weeks_in_year,
                gregorian_to_week_date, week_of_month, weekday_abbr, weekday_name,
                _iso_info, _iso_num_weeks, _gregorian_to_iso, _iso_week_of_month)
        self.assertIs(week_info, _iso_info)
        self.assertIs(num_weeks_in_year, _iso_num_weeks)
        self.assertIs(gregorian_to_week_date, _gregorian_to_iso)
        self.assertIs(week_of_month, _iso_week_of_month)
        self.assertEqual(weekday_abbr, ("Mon","Tue","Wed","Thu","Fri","Sat","Sun"))
        self.assertEqual(weekday_name, ("Monday","Tuesday","Wednesday","Thursday",
                                        "Friday","Saturday","Sunday"))

    @override('en-au')
    def testSundayStartingWeek(self):
        # FIRST_DAY_OF_WEEK is Sunday for Australia
        self.assertEqual(get_format('FIRST_DAY_OF_WEEK'), 0)
        importlib.reload(ls.joyous.utils.weeks)
        from ls.joyous.utils.weeks import (week_info, num_weeks_in_year,
                gregorian_to_week_date, week_of_month, weekday_abbr, weekday_name,
                _ssweek_info, _ssweek_num_weeks, _gregorian_to_ssweek, _ssweek_of_month)
        self.assertIs(week_info, _ssweek_info)
        self.assertIs(num_weeks_in_year, _ssweek_num_weeks)
        self.assertIs(gregorian_to_week_date, _gregorian_to_ssweek)
        self.assertIs(week_of_month, _ssweek_of_month)
        self.assertEqual(weekday_abbr, ("Sun","Mon","Tue","Wed","Thu","Fri","Sat"))
        self.assertEqual(weekday_name, ("Sunday","Monday","Tuesday","Wednesday","Thursday",
                                        "Friday","Saturday"))

    def testFirstDayOfWeek(self):
        with override_settings(JOYOUS_FIRST_DAY_OF_WEEK = 0):
            importlib.reload(ls.joyous.utils.weeks)
            from ls.joyous.utils.weeks import weekday_abbr
            self.assertEqual(weekday_abbr, ("Sun","Mon","Tue","Wed","Thu","Fri","Sat"))

        with override_settings(JOYOUS_FIRST_DAY_OF_WEEK = 1):
            importlib.reload(ls.joyous.utils.weeks)
            from ls.joyous.utils.weeks import weekday_abbr
            self.assertEqual(weekday_abbr, ("Mon","Tue","Wed","Thu","Fri","Sat","Sun"))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
