# ------------------------------------------------------------------------------
# Holidays settings parser
# ------------------------------------------------------------------------------
from __future__ import unicode_literals
import re
from .. import holidays

__all__ = ["parseHolidays"]

def _createMap(symbols):
    holidayMap = {}
    for (name, cls) in symbols:
        if (type(cls) is type(object) and
            issubclass(cls, holidays.HolidayBase) and
            cls is not holidays.HolidayBase):
            holidayMap[name] = cls
            obj = cls()
            if hasattr(obj, "country"):
                holidayMap.setdefault(obj.country, cls)
    return holidayMap
_HOLIDAY_MAP = _createMap(holidays.__dict__.items())

HolsRe = re.compile(r"(\w[\w\ ]*)(\[.+?\])?")
SplitRe = re.compile(r",\s*")

def _parseSubdivisions(holidaysStr, cls):
    # * = all states and provinces
    retval = 0
    if holidaysStr[0] != '[' or holidaysStr[-1] != ']':
        return retval
    provinces = getattr(cls, "PROVINCES", [])
    states = getattr(cls, "STATES", [])

    for subdivision in SplitRe.split(holidaysStr[1:-1]):
        subdivision = subdivision.strip()
        if subdivision == "*":
            retval += sum(cls(state = subdivision) for subdivision in states)
            retval += sum(cls(prov = subdivision) for subdivision in provinces)
        else:
            if subdivision in states:
                retval += cls(state = subdivision)
            else:
                retval += cls(prov = subdivision)
    return retval

def parseHolidays(holidaysStr, holidayMap=None):
    """
    Takes a string like NZ[WTL,Nelson],AU[*],Northern Ireland and builds a HolidaySum from it
    """
    if holidayMap is None:
        holidayMap = _HOLIDAY_MAP
    retval = holidays.HolidayBase()
    retval.country = None
    holidaysStr = holidaysStr.strip()
    for (country, subdivisions) in HolsRe.findall(holidaysStr):
        cls = holidayMap.get(country)
        if cls is not None:
            if subdivisions:
                retval += _parseSubdivisions(subdivisions, cls)
            else:
                retval += cls()
    return retval

