# ------------------------------------------------------------------------------
# Test Event Category
# ------------------------------------------------------------------------------
import sys
from django.test import TestCase
from ls.joyous.models import EventCategory

# ------------------------------------------------------------------------------
class Test(TestCase):
    def testDefaultInit(self):
        cat = EventCategory()
        self.assertEqual(cat.code, "")
        self.assertEqual(cat.name, "")
        self.assertEqual(str(cat), "")

    def testInit(self):
        cat = EventCategory(code="A1", name="AlphaOne")
        self.assertEqual(cat.code, "A1")
        self.assertEqual(cat.name, "AlphaOne")
        self.assertEqual(str(cat), "AlphaOne")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
