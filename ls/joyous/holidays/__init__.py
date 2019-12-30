# ------------------------------------------------------------------------------
# Joyous Holidays
# ------------------------------------------------------------------------------
import datetime as dt
from collections import OrderedDict
from django.conf import settings
from .parser import parseHolidays

class Holidays:
    """Defines what holidays are celebrated on what dates."""
    def __init__(self):
        self.simple = {}
        self.srcs = [ self.simple ]
        self._parseSettings()

    def _parseSettings(self):
        holidaySettings = getattr(settings, "JOYOUS_HOLIDAYS", "")
        if holidaySettings:
            hols = parseHolidays(holidaySettings)
            if hols is not None:
                self.register(hols)

    def register(self, src):
        """Register a new source of holiday data."""
        self.srcs.append(src)

    def add(self, date, value):
        """Add a holiday to an individual date."""
        oldValue = self.simple.get(date)
        if oldValue:
            if oldValue not in value and value not in oldValue:
                self.simple[date] = "{}, {}".format(oldValue, value)
        else:
            self.simple[date] = value

    def get(self, date):
        """Get all the holidays that are celebrated on this date."""
        holidays = []
        for src in self.srcs:
            # get from python-holidays and other dict type srcs
            getHoliday = getattr(src, "get", None)
            if not getHoliday:
                # get from workalendar srcs
                getHoliday = getattr(src, "get_holiday_label")
            holiday = getHoliday(date)
            if holiday:
                holidays.extend(holiday.split(", "))
        holidays = list(OrderedDict.fromkeys(holidays))   # remove duplicates
        return ", ".join(holidays)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
