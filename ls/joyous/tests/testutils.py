#---------------------------------------------------------------------------
# Testing infrastructure
#---------------------------------------------------------------------------
import unittest
import datetime as dt
from functools import wraps
from django.utils import timezone


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


def datetimetz(*args):
    if len(args) < 2:
        return timezone.localtime()
    if type(args[0]) == int:
        datetime = dt.datetime(*args)
    elif type(args[0]) == dt.date:
        datetime = dt.datetime.combine(*args)
    return timezone.make_aware(datetime)
