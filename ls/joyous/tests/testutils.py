#---------------------------------------------------------------------------
# Testing infrastructure
#---------------------------------------------------------------------------
import unittest
import datetime as dt
from functools import wraps
from django.utils import timezone
from dateutil import parser
from wagtail.core.models import Site, Page
from freezegun import freeze_time

# ------------------------------------------------------------------------------
def skipUnlessSetup(attrs):
    if type(attrs) == str:
        attrs = [attrs]
    def decorator(func):
        @wraps(func)
        def test(self, *args, **kwargs):
            for attr in attrs:
                if not hasattr(self, attr):
                    self.skipTest("{} not setup".format(attr))
            return func(self, *args, **kwargs)
        return test
    return decorator

# ------------------------------------------------------------------------------
def datetimetz(*args):
    if len(args) < 2:
        return timezone.localtime()
    if type(args[0]) == int:
        datetime = dt.datetime(*args)
    elif type(args[0]) == dt.date:
        datetime = dt.datetime.combine(*args)
    return timezone.make_aware(datetime)

# ------------------------------------------------------------------------------
__abracadabra = object()

def freeze_timetz(time_to_freeze=None, tz_offset=__abracadabra,
                  *args, **kwargs):
    if tz_offset is not __abracadabra:
        raise TypeError("Use plain freeze_time if you want to pass a tz_offset")

    if time_to_freeze is None:
        time_to_freeze = timezone.localtime().replace(tzinfo=None)
    elif isinstance(time_to_freeze, dt.date):
        time_to_freeze = dt.datetime.combine(time_to_freeze, dt.datetime.time())
    elif isinstance(time_to_freeze, str):
        time_to_freeze = parser.parse(time_to_freeze)

    if (isinstance(time_to_freeze, dt.datetime) and
        timezone.is_naive(time_to_freeze)):
        time_to_freeze = timezone.make_aware(time_to_freeze)

    return freeze_time(time_to_freeze, *args, **kwargs)

# ------------------------------------------------------------------------------
def getPage(path):
    return Page.objects.get(url_path=path).specific

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
