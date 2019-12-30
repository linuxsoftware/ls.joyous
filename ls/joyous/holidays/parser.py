# ------------------------------------------------------------------------------
# Holidays settings parser
# ------------------------------------------------------------------------------
from __future__ import unicode_literals
import re
import holidays as python_holidays

__all__ = ["parseHolidays"]

def _createMap(symbols):
    holidayMap = {}
    for (name, cls) in symbols:
        if (type(cls) is type(object) and
            issubclass(cls, python_holidays.HolidayBase) and
            cls is not python_holidays.HolidayBase):
            holidayMap[name] = cls
            obj = cls()
            if hasattr(obj, "country"):
                holidayMap.setdefault(obj.country, cls)
    return holidayMap
_PYTHON_HOLIDAYS_MAP = _createMap(list(python_holidays.__dict__.items()))

HolsRe = re.compile(r"(\w[\w\ ]*|\*)(\[.+?\])?")
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
            retval = 0
            subval = sum(cls(state = subdivision) for subdivision in states)
            retval += subval
            subval = sum(cls(prov = subdivision) for subdivision in provinces)
            retval += subval
            break
        else:
            if subdivision in states:
                retval += cls(state = subdivision)
            elif subdivision in provinces:
                retval += cls(prov = subdivision)
    return retval

def parseHolidays(holidaysStr, holidayMap=None):
    """
    Takes a string like NZ[WTL,Nelson],AU[*],Northern Ireland and builds a HolidaySum from it
    """
    if holidayMap is None:
        holidayMap = _PYTHON_HOLIDAYS_MAP
    retval = 0
    holidaysStr = holidaysStr.strip()
    for (country, subdivisions) in HolsRe.findall(holidaysStr):
        if country == "*":
            retval = 0
            for cls in holidayMap.values():
                if subdivisions:
                    subval = _parseSubdivisions(subdivisions, cls)
                    retval += subval
                else:
                    retval += cls()
            break
        cls = holidayMap.get(country)
        if cls is not None:
            if subdivisions:
                subval = _parseSubdivisions(subdivisions, cls)
                retval += subval
            else:
                retval += cls()
    if retval is 0:
        retval = None
    return retval

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
