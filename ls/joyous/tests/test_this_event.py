# ------------------------------------------------------------------------------
# Test ThisEvent
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django_bs_test import TestCase
from django.contrib.auth.models import User
from wagtail.models import Page
from ls.joyous.models import SpecificCalendarPage
from ls.joyous.models import SimpleEventPage, ThisEvent

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = SpecificCalendarPage(owner = self.user,
                                             slug  = "events",
                                             title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.page = SimpleEventPage(owner = self.user,
                                    slug   = "agfest",
                                    title  = "AgFest",
                                    date   = dt.date(2015,6,5),
                                    time_from = dt.time(11),
                                    time_to   = dt.time(17,30))
        self.calendar.add_child(instance=self.page)
        self.page.save_revision().publish()

    def testInit(self):
        event = ThisEvent(self.page, title="Mud mud mud")
        self.assertEqual(event.page, self.page)
        self.assertEqual(event.title, "Mud mud mud")
        self.assertEqual(event.url, "/events/agfest/")

    def testInit2Args(self):
        with self.assertRaises(TypeError):
            event = ThisEvent(self.page, "Mud mud mud")

    def testRepr(self):
        event = ThisEvent(self.page, url="/events/muddy/")
        self.assertEqual(repr(event),
                         "ThisEvent (title='AgFest', "
                         "page=<SimpleEventPage: AgFest>, "
                         "url='/events/muddy/')")

    def testPageAttrs(self):
        event = ThisEvent(self.page)
        self.assertEqual(event.title, "AgFest")
        self.assertEqual(event.slug, "agfest")
        self.assertEqual(event.date, dt.date(2015,6,5))

    def testTheseAttrs(self):
        event = ThisEvent(self.page)
        event.title = "Mud"
        event.url = "/events/muddy/"
        self.assertEqual(event.title, "Mud")
        self.assertEqual(self.page.title, "AgFest")
        self.assertEqual(event.url, "/events/muddy/")
        self.assertEqual(self.page.url, "/events/agfest/")

    def testNewAttrs(self):
        event = ThisEvent(self.page, foo="foo")
        event.bar = "bar"
        self.assertTrue(hasattr(event, "foo"))
        self.assertFalse(hasattr(self.page, "foo"))
        self.assertEqual(event.foo, "foo")
        self.assertTrue(hasattr(event, "bar"))
        self.assertFalse(hasattr(self.page, "bar"))
        self.assertEqual(event.bar, "bar")

# ------------------------------------------------------------------------------
class TestBackCompat(TestCase):
    """
    ThisEvent maintains backwards compatibility with the namedtuple it used to be
    """
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = SpecificCalendarPage(owner = self.user,
                                             slug  = "events",
                                             title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.page = SimpleEventPage(owner = self.user,
                                    slug   = "agfest",
                                    title  = "AgFest",
                                    date   = dt.date(2015,6,5),
                                    time_from = dt.time(11),
                                    time_to   = dt.time(17,30))
        self.calendar.add_child(instance=self.page)
        self.page.save_revision().publish()

    def testNamedAttrs(self):
        event = ThisEvent("Mud mud mud", self.page, "/events/muddy/")
        self.assertEqual(event.title, "Mud mud mud")
        self.assertEqual(event.page, self.page)
        self.assertEqual(event.url, "/events/muddy/")

    def testExplode(self):
        event = ThisEvent("Mud mud mud", self.page, "/events/muddy/")
        title, page, url = event
        self.assertEqual(title, "Mud mud mud")
        self.assertEqual(page, self.page)
        self.assertEqual(url, "/events/muddy/")

    def testItems(self):
        event = ThisEvent("Mud mud mud", self.page, "/events/muddy/")
        self.assertEqual(len(event), 3)
        self.assertEqual(event[0], "Mud mud mud")
        self.assertEqual(event[1], self.page)
        self.assertEqual(event[2], "/events/muddy/")

    def testSlice(self):
        event = ThisEvent("Mud mud mud", self.page, "/events/muddy/")
        title, page = event[:2]
        self.assertEqual(title, "Mud mud mud")
        self.assertEqual(page, self.page)

    def testAsDict(self):
        event = ThisEvent("Mud mud mud", self.page, "/events/muddy/")
        attrs = event._asdict()
        self.assertEqual(attrs['title'], "Mud mud mud")
        self.assertEqual(attrs['page'], self.page)
        self.assertEqual(attrs['url'], "/events/muddy/")

    def testQuery(self):
        events = list(SimpleEventPage.events.this())
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertTrue(isinstance(event, ThisEvent))
        self.assertEqual(event.title, "AgFest")
        self.assertEqual(event.page, self.page)
        self.assertEqual(event.url, "/events/agfest/")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
