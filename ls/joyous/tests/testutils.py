#---------------------------------------------------------------------------
# Testing infrastructure
#---------------------------------------------------------------------------
import unittest
from functools import wraps


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


