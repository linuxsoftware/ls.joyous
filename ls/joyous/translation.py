from modeltranslation.translator import TranslationOptions
from modeltranslation.decorators import register
from ls.joyous.models import GroupPage, EventBase, EventCategory, SimpleEventPage, MultidayEventPage, RecurringEventPage, ExtraInfoPage, CalendarPage

@register(GroupPage)
class GroupPageTR(TranslationOptions):
    fields = (
        'content',
    )

@register(EventBase)
class EventBaseTR(TranslationOptions):
    fields = (
        'details',
        'location',
        'website',
    )

@register(EventCategory)
class EventCategoryTR(TranslationOptions):
    fields = (
        'name',
    )

@register(SimpleEventPage)
class SimpleEventPageTR(TranslationOptions):
    fields = ()

@register(MultidayEventPage)
class SimpleEventPageTR(TranslationOptions):
    fields = ()

@register(RecurringEventPage)
class RecurringEventPageTR(TranslationOptions):
    fields = ()

@register(CalendarPage)
class CalendarPageTR(TranslationOptions):
    fields = (
        'intro',
    )

@register(ExtraInfoPage)
class ExtraInfoPageTR(TranslationOptions):
    fields = (
        'extra_title',
        'extra_information',
    )

