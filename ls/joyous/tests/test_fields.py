# ------------------------------------------------------------------------------
# Test Fields
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import connection, models
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import YEARLY, WEEKLY, MONTHLY
from ls.joyous.utils.recurrence import MO, TU, WE, TH, FR, SA, SU
from ls.joyous.fields import (RecurrenceField, RecurrenceFormField,
                              MultipleSelectField, MultipleSelectFormField)
from .testutils import datetimetz, freeze_timetz, getPage

# ------------------------------------------------------------------------------
class TestRecurrenceField(TestCase):
    def setUp(self):
        self.rr = Recurrence(dtstart=dt.date(2011, 12, 13),
                             freq=MONTHLY, byweekday=MO(1))
        self.ical = "DTSTART:20111213\nRRULE:FREQ=MONTHLY;WKST=SU;BYDAY=+1MO"

    def testInit(self):
        field = RecurrenceField()
        self.assertEqual(field.max_length, 255)
        self.assertEqual(field.description, "The rule for recurring events")
        self.assertEqual(field.get_internal_type(), "CharField")
        self.assertEqual(field.db_type(connection), "varchar(255)")
        self.assertIsInstance(field.formfield(), RecurrenceFormField)

    def testDeconstruct(self):
        field = RecurrenceField(name="time_after_time")
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(name, "time_after_time")
        self.assertEqual(path, "ls.joyous.fields.RecurrenceField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {})

    def testToPython(self):
        field = RecurrenceField()
        self.assertIsNone(field.to_python(None))
        self.assertIsNone(field.to_python(""))
        self.assertEqual(field.to_python(self.rr), self.rr)
        self.assertEqual(field.to_python(self.ical), self.rr)
        with self.assertRaises(ValidationError):
            field.to_python("ABCD")

    def testGetPrepValue(self):
        field = RecurrenceField()
        self.assertEqual(field.get_prep_value(self.rr),
                         self.ical)

    def testGetPrepLookup(self):
        field = RecurrenceField()
        with self.assertRaises(TypeError):
            field.get_prep_lookup("exact", self.rr)

# ------------------------------------------------------------------------------
class TestMultipleSelectField(TestCase):
    def setUp(self):
        self.choices = [('A', "Dawn"),
                        ('B', "Day"),
                        ('C', "Dusk"),
                        ('D', "Night")]
        self.opts = ["B", "C", "D"]
        self.strval = "B,C,D"

    def testInit(self):
        field = MultipleSelectField(choices=self.choices)
        self.assertEqual(field.max_length, 255)
        self.assertEqual(field.description, "Field of type: MultipleSelectField")
        self.assertEqual(field.get_internal_type(), "CharField")
        self.assertEqual(field.db_type(connection), "varchar(255)")
        self.assertIsInstance(field.formfield(), MultipleSelectFormField)

    def testDeconstruct(self):
        field = MultipleSelectField(name="attention", choices=self.choices)
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(name, "attention")
        self.assertEqual(path, "ls.joyous.fields.MultipleSelectField")
        self.assertEqual(args, [])
        self.assertEqual(kwargs, {'choices': self.choices})

    def testToPython(self):
        field = MultipleSelectField(choices=self.choices)
        self.assertEqual(field.to_python(None), [])
        self.assertEqual(field.to_python(""), [])
        self.assertEqual(field.to_python(self.opts), self.opts)
        self.assertEqual(field.to_python(self.strval), self.opts)
        self.assertEqual(field.to_python("A"), ["A"])

    def testGetPrepValue(self):
        field = MultipleSelectField(choices=self.choices)
        self.assertEqual(field.get_prep_value(self.opts), self.strval)

    def testGetPrepLookup(self):
        field = MultipleSelectField(choices=self.choices)
        with self.assertRaises(TypeError):
            field.get_prep_lookup("exact", self.opts)

    def testCoerceChoice(self):
        field = MultipleSelectField(choices=self.choices)
        self.assertEqual(field._coerceChoice("A"), "A")
        with self.assertRaises(ValidationError):
            field._coerceChoice("X")

    def testContributeToClass(self):
        class Foo(models.Model):
            class Meta:
                app_label = "foo"
            field = MultipleSelectField(choices=self.choices)
        self.assertTrue(hasattr(Foo, "get_field_display"))
        foo = Foo(field="A")
        self.assertEqual(foo.get_field_display(), "Dawn")

    def testValidate(self):
        field = MultipleSelectField(choices=self.choices, null=False, blank=False)
        with self.assertRaises(ValidationError):
            field.validate(None, None)
        with self.assertRaises(ValidationError):
            field.validate("", None)

    def testValidateRO(self):
        field = MultipleSelectField(choices=self.choices, editable=False)
        field.validate(None, None)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
