# ------------------------------------------------------------------------------
# Test Middleware
# ------------------------------------------------------------------------------
import sys
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.utils.timezone import get_current_timezone_name
from wagtail.users.models import UserProfile
from ls.joyous.middleware import UserTimeZoneMiddleware

# ------------------------------------------------------------------------------
class TestUserTimeZone(TestCase):
    def testLogInLogOut(self):
        self.assertEqual(get_current_timezone_name(), "Asia/Tokyo")
        self._login()
        self.assertEqual(get_current_timezone_name(), "America/Toronto")
        self._logout()
        self.assertEqual(get_current_timezone_name(), "Asia/Tokyo")

    def _login(self):
        midware = UserTimeZoneMiddleware()
        request = RequestFactory().get("/test")
        request.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        UserProfile.objects.create(user=request.user,
                                   preferred_language="en",
                                   current_time_zone="America/Toronto")
        request.session = {}
        midware.process_request(request)

    def _logout(self):
        midware = UserTimeZoneMiddleware()
        request = RequestFactory().get("/test")
        request.user = AnonymousUser()
        request.session = {}
        midware.process_request(request)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
