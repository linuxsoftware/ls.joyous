# ------------------------------------------------------------------------------
# Test Hooks
# ------------------------------------------------------------------------------
import sys
from unittest.mock import Mock, patch
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage, CalendarPageForm
from ls.joyous.wagtail_hooks import handlePageExport, stashRequest

# ------------------------------------------------------------------------------
class TestWagtailHooks(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@j.test', 's3(r3t')
        self.page = CalendarPage(owner  = self.user,
                                 slug  = "events",
                                 title = "Events")
        self.home.add_child(instance=self.page)
        self.page.save_revision().publish()

    @patch("ls.joyous.wagtail_hooks.ICalHandler")
    def testICalExport(self, Handler):
        request = RequestFactory().get("/test?format=ical")
        handlePageExport(self.page, request, [], {})
        Handler.assert_called_with()
        Handler().serve.assert_called_with(self.page, request, [], {})

    @patch("ls.joyous.wagtail_hooks.GoogleCalendarHandler")
    def testGoogleExport(self, Handler):
        request = RequestFactory().get("/test?format=google")
        handlePageExport(self.page, request, [], {})
        Handler.assert_called_with()
        Handler().serve.assert_called_with(self.page, request, [], {})

    @patch("ls.joyous.wagtail_hooks.RssHandler")
    def testRssExport(self, Handler):
        request = RequestFactory().get("/test?format=rss")
        handlePageExport(self.page, request, [], {})
        Handler.assert_called_with()
        Handler().serve.assert_called_with(self.page, request, [], {})

    @patch("ls.joyous.wagtail_hooks.NullHandler")
    def testNullExport(self, Handler):
        request = RequestFactory().get("/test")
        handlePageExport(self.page, request, [], {})
        Handler.assert_called_with()
        Handler().serve.assert_called_with(self.page, request, [], {})

    def testStashRequest(self):
        request = RequestFactory().get("/test")
        stashRequest(request, self.page)
        self.assertEqual(getattr(self.page, '__joyous_edit_request'), request)
        delattr(self.page, '__joyous_edit_request')

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
