# ------------------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------------------
import pytz
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin


class UserTimeZoneMiddleware(MiddlewareMixin):
    """
    If there is a Wagtail user with their time zone set then activate
    that time zone for all pages (not just the Wagtail Admin).
    """
    def process_request(self, request):
        try:
            tzname = request.user.wagtail_userprofile.current_time_zone
        except AttributeError:
            tzname = None
        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()
