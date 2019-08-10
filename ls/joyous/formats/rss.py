# ------------------------------------------------------------------------------
# RSS Feed Export Handler
# ------------------------------------------------------------------------------
import datetime as dt
from calendar import timegm
from collections import OrderedDict
from urllib.parse import urlencode
import pytz
from icalendar import vPeriod
from django.http import HttpResponse
from django.utils import html
from django.utils.http import http_date
from django.template import TemplateDoesNotExist, loader
from django.templatetags.static import static
from ..models import CalendarPage
from ..utils.telltime import getAwareDatetime
from feedgen.feed import FeedGenerator
from feedgen.entry import FeedEntry
from .errors import CalendarTypeError, CalendarNotInitializedError

# ------------------------------------------------------------------------------
class RssHandler:
    """Serve a RSS Feed"""
    def serve(self, page, request, *args, **kwargs):
        try:
            feed = CalendarFeed.fromPage(page, request)
        except CalendarTypeError:
            return None
        response = HttpResponse(feed.rss_str(),
                                content_type='application/xml; charset=utf-8')
        return response

# ------------------------------------------------------------------------------
def fullUrl(url, page, request):
    """Convert a relative url to a full url"""
    siteId, root, path = page.get_url_parts(request)
    if not url.startswith(root):
        url = root + url
    return url

# ------------------------------------------------------------------------------
class CalendarFeed(FeedGenerator):
    """Produce a feed of upcoming events"""
    imagePath = "joyous/img/logo.png"

    @classmethod
    def fromPage(cls, page, request):
        if isinstance(page, CalendarPage):
            return cls._fromCalendarPage(page, request)
        else:
            raise CalendarTypeError("Unsupported input page")

    @classmethod
    def _fromCalendarPage(cls, page, request):
        feed = cls()
        feed.title(page.title)
        feed.link(href=page.get_full_url(request))
        feed.author(name=page.owner.get_full_name())
        feed.description(page.intro or page.title)
        feed.generator("ls.joyous")
        feed.image(url=fullUrl(static(cls.imagePath), page, request))

        for event in page._getUpcomingEvents(request):
            entry = EventEntry.fromEvent(event, request)
            feed.entry(entry)
        return feed


# ------------------------------------------------------------------------------
class EventEntry(FeedEntry):
    templatePath = "joyous/formats/rss.xml"

    @classmethod
    def fromEvent(cls, event, request):
        page = event.page
        entry = cls()
        entry.title(event.title)
        url = fullUrl(event.url, page, request)
        entry.link(href=url)
        entry.guid(url, permalink=True)
        # entry.id(page.uid)
        entry.setDescription(event, request)
        entry.setCategory(page)
        entry.setImage(page, request)
        entry.author(name=page.owner.get_full_name())
        entry.published(page.first_published_at)
        entry.updated(page.last_published_at)
        return entry

    def setDescription(self, event, request):
        tmpl = loader.get_template(self.templatePath)
        ctxt = {'event':   event.page,
                'title':   event.title,
                'request': request}
        self.description(tmpl.render(ctxt, request))

    def setCategory(self, page):
        category = page.category
        if category:
            self.category(term=category.name)

    def setImage(self, page, request):
        image = page.image
        if image:
            ren = image.get_rendition("width-350|format-png")
            self.enclosure(url=fullUrl(ren.url, page, request),
                           length=str(len(ren.file)),
                           type="image/png")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
