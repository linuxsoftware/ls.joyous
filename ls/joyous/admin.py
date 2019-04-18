from django.contrib import admin
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, MultidayRecurringEventPage,
        CancellationPage, ExtraInfoPage, PostponementPage,
        RescheduleMultidayEventPage, GroupPage,
        CalendarPage, GeneralCalendarPage, SpecificCalendarPage)

# Register your models here.
admin.site.register(SimpleEventPage)
admin.site.register(MultidayEventPage)
admin.site.register(RecurringEventPage)
admin.site.register(CancellationPage)
admin.site.register(ExtraInfoPage)
admin.site.register(PostponementPage)
admin.site.register(CalendarPage)
admin.site.register(GroupPage)




