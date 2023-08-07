# ------------------------------------------------------------------------------
# Test Forms
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.models import Page
from ls.joyous.forms import (FormDefender, FormClassOverwriteWarning,
                             FormCannotAssimilateWarning)
from ls.joyous.models import CalendarPage
from ls.joyous.models.one_off_events import MultidayEventPage as MEP
from ls.joyous.models.one_off_events import MultidayEventPageForm as MEPForm


# ------------------------------------------------------------------------------
class NewPageForm(WagtailAdminPageForm):
    def clean(self):
        # take a copy of cleaned_data so add_error does not remove fields
        cleaned_data = dict(super().clean())
        startDate = cleaned_data.get('date_from', dt.date.min)
        endDate   = cleaned_data.get('date_to', dt.date.max)
        msg = 'Choose a date in this Millennium'
        if startDate.year <= 2000:
            self.add_error('date_from', msg)
        if endDate.year <= 2000:
            self.add_error('date_to', msg)
        return cleaned_data

    def save(self, commit=True):
        buck = User.objects.create_user('buck', 'buck@nasa.gov', 'w!Lm@')
        page = super().save(commit=False)
        page.owner = buck
        if commit:
            page.save()
        return page

class NewMEPForm(MEPForm):
    pass

class PlainPageForm(WagtailAdminPageForm):
    pass

class PlainPage(Page, metaclass=FormDefender):
    class Meta:
        abstract = True
    base_form_class = PlainPageForm

class Test(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        for Pg, PgForm in [(MEP, MEPForm), (PlainPage, PlainPageForm)]:
            Pg._base_form_class = PgForm
            Pg.get_edit_handler.cache_clear()
            if hasattr(PgForm, 'assimilated_class'):
                del PgForm.assimilated_class

    def testType(self):
        self.assertIs(type(MEP), FormDefender)

    def testNew(self):
        self.assertTrue('_base_form_class' in MEP.__dict__)
        self.assertFalse('base_form_class' in MEP.__dict__)

    def testGet(self):
        self.assertTrue(hasattr(MEP, 'base_form_class'))
        self.assertEqual(MEP.base_form_class, MEPForm)

    def testSetNone(self):
        with self.assertWarns(FormClassOverwriteWarning):
            MEP.base_form_class = None
        self.assertIs(MEP.base_form_class, None)

    def testSetNewForm(self):
        with self.assertWarns(FormClassOverwriteWarning):
            MEP.base_form_class = NewPageForm
        self.assertEqual(MEP.base_form_class, NewPageForm)

    def testSetNewFromNone(self):
        MEP._base_form_class = None
        MEP.base_form_class = NewPageForm
        self.assertEqual(MEP.base_form_class, NewPageForm)

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testSetSubclass(self):
        MEP.base_form_class = NewMEPForm
        self.assertEqual(MEP.base_form_class, NewMEPForm)

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testDefend(self):
        MEP.base_form_class = None
        self.assertIs(MEP.base_form_class, MEPForm)

    def testAssimilate(self):
        MEPForm.assimilate(NewPageForm)
        self.assertEqual(MEPForm.assimilated_class, NewPageForm)

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testAssimilated(self):
        MEP.base_form_class = NewPageForm
        self.assertIs(MEP.base_form_class, MEPForm)
        Form = MEP.get_edit_handler().get_form_class()
        self.assertTrue(issubclass(Form, MEPForm))
        form = Form({'slug':      "C2C",
                     'title':     "Coast to Coast",
                     'date_from': "2021-02-12",
                     'date_to':   "2021-02-13",
                     'tz':        "Pacific/Auckland"})
        self.assertIsInstance(form.assimilated, NewPageForm)
        self.assertEqual(form.assimilated.fields.keys(), form.fields.keys())
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.errors, {})

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testAssimilatedClean(self):
        MEP.base_form_class = NewPageForm
        Form = MEP.get_edit_handler().get_form_class()
        form = Form({'slug':      "C2C",
                     'title':     "Coast to Coast",
                     'date_from': "1987-02-08",
                     'date_to':   "1987-02-07",
                     'tz':        "Pacific/Auckland"})
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'date_from': ["Choose a date in this Millennium"],
                              'date_to':   ["Choose a date in this Millennium",
                                            "Event cannot end before it starts",]})

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testAssimilatedSave(self):
        user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        calendar = CalendarPage(owner = user,
                                slug  = "events",
                                title = "Events")
        home = Page.objects.get(slug='home')
        home.add_child(instance=calendar)
        calendar.save_revision().publish()
        event = MEP(owner = user,
                    slug  = "allnighter",
                    title = "All Night",
                    date_from = dt.date(2012,12,31),
                    date_to   = dt.date(2013,1,1),
                    time_from = dt.time(23),
                    time_to   = dt.time(3))
        calendar.add_child(instance=event)
        event.save_revision().publish()
        MEP.base_form_class = NewPageForm
        Form = MEP.get_edit_handler().get_form_class()
        form = Form(instance=event, parent_page=calendar)
        page = form.save()
        self.assertEqual(page.owner.username, "buck")

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testNoneAssimilated(self):
        MEP.base_form_class = None
        self.assertIs(MEP.base_form_class, MEPForm)
        Form = MEP.get_edit_handler().get_form_class()
        self.assertTrue(issubclass(Form, MEPForm))
        form = Form({'slug':      "C2C",
                     'title':     "Coast to Coast",
                     'date_from': "2021-02-12",
                     'date_to':   "2021-02-13",
                     'tz':        "Pacific/Auckland"})
        self.assertIsInstance(form.assimilated, type(None))
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.errors, {})

    @override_settings(JOYOUS_DEFEND_FORMS=True)
    def testDefendNonBorg(self):
        with self.assertWarns(FormCannotAssimilateWarning):
            PlainPage.base_form_class = NewPageForm
        self.assertEqual(PlainPage.base_form_class, PlainPageForm)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
