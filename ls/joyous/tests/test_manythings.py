# ------------------------------------------------------------------------------
# Test Many Things Utilities
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.test import TestCase
from django.utils import translation
from ls.joyous.utils.manythings import toOrdinal, hrJoin

# ------------------------------------------------------------------------------
class Test(TestCase):
    def testToOrdinal(self):
        self.assertEqual(toOrdinal(1), "first")
        self.assertEqual(toOrdinal(2), "second")
        self.assertEqual(toOrdinal(3), "third")
        self.assertEqual(toOrdinal(4), "fourth")
        self.assertEqual(toOrdinal(5), "fifth")

    def testToOrdinalNum(self):
        self.assertEqual(toOrdinal(6), "6th")
        self.assertEqual(toOrdinal(11), "11th")
        self.assertEqual(toOrdinal(12), "12th")
        self.assertEqual(toOrdinal(13), "13th")
        self.assertEqual(toOrdinal(21), "21st")
        self.assertEqual(toOrdinal(102), "102nd")
        self.assertEqual(toOrdinal(6543), "6543rd")

    def testLastToOrdinal(self):
        self.assertEqual(toOrdinal(-1), "last")

    def testPenultimateToOrdinal(self):
        self.assertEqual(toOrdinal(-2), "penultimate")

    def testHumanReadableJoin(self):
        self.assertEqual(hrJoin([""]), "")
        self.assertEqual(hrJoin(["ice"]), "ice")
        self.assertEqual(hrJoin(["ice", "fire"]), "ice and fire")
        self.assertEqual(hrJoin(["wind", "ice", "fire"]),
                         "wind, ice and fire")
        self.assertEqual(hrJoin(["dog", "cat", "hen", "yak", "ant"]),
                         "dog, cat, hen, yak and ant")

# ------------------------------------------------------------------------------
class  TestFrançais(TestCase):
    def setUp(self):
        translation.activate('fr')

    def tearDown(self):
        translation.deactivate()

    def testToOrdinal(self):
        self.assertEqual(toOrdinal (1), "premier")
        self.assertEqual(toOrdinal (2), "deuxième")
        self.assertEqual(toOrdinal (3), "troisième")
        self.assertEqual(toOrdinal (4), "quatrième")
        self.assertEqual(toOrdinal (5), "cinquième")

    def testToOrdinalNum(self):
        self.assertEqual(toOrdinal(6), "6me")
        self.assertEqual(toOrdinal(11), "11er")
        self.assertEqual(toOrdinal(12), "12me")
        self.assertEqual(toOrdinal(13), "13me")
        self.assertEqual(toOrdinal(21), "21er")
        self.assertEqual(toOrdinal(102), "102me")
        self.assertEqual(toOrdinal(6543), "6543me")

    def testLastToOrdinal(self):
        self.assertEqual(toOrdinal(-1), "dernier")

    def testPenultimateToOrdinal(self):
        self.assertEqual(toOrdinal(-2), "avant-dernier")

    def testHumanReadableJoin(self):
        self.assertEqual(hrJoin([""]), "")
        self.assertEqual(hrJoin (["glace"]), "glace")
        self.assertEqual(hrJoin (["glace", "feu"]), "glace et feu")
        self.assertEqual(hrJoin (["vent", "glace", "feu"]),
                         "vent, glace et feu")
        self.assertEqual(hrJoin (["chien", "chat", "poule", "yak", "fourmi"]),
                         "chien, chat, poule, yak et fourmi")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
