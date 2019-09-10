Calendar
========
.. automodule:: ls.joyous.models

CalendarPage
------------
.. inheritance-diagram:: CalendarPage
    :top-classes: wagtail.core.models.Page
    :parts: 1
.. autoclass:: CalendarPage
    :show-inheritance:

    .. attribute:: holidays
    
        The holidays to be displayed by this calendar.

    .. attribute:: intro

        Introductory text.

    .. attribute:: view_choices

        What types of calendar views the user can select.

    .. attribute:: default_view

        The default calendar view to display to the user.

    .. automethod:: routeDefault
    .. automethod:: routeByMonthAbbr
    .. automethod:: serveMonth
    .. automethod:: serveWeek
    .. automethod:: serveDay
    .. automethod:: serveUpcoming
    .. automethod:: servePast
    .. automethod:: serveMiniMonth

    .. automethod:: can_create_at
    .. automethod:: _allowAnotherAt
    .. automethod:: peers

    .. automethod:: _getEventsOnDay
    .. automethod:: _getEventsByDay
    .. automethod:: _getEventsByWeek
    .. automethod:: _getUpcomingEvents
    .. automethod:: _getPastEvents
    .. automethod:: _getEventFromUid
    .. automethod:: _getAllEvents


SpecificCalendarPage
--------------------
.. inheritance-diagram:: SpecificCalendarPage
    :top-classes: ls.joyous.models.calendar.CalendarPage
    :parts: 1
.. autoclass:: SpecificCalendarPage
    :show-inheritance:

    .. automethod:: _allowAnotherAt
    .. automethod:: _getEventsByDay
    .. automethod:: _getEventsByWeek
    .. automethod:: _getUpcomingEvents
    .. automethod:: _getPastEvents
    .. automethod:: _getEventFromUid
    .. automethod:: _getAllEvents

GeneralCalendarPage
-------------------
.. inheritance-diagram:: GeneralCalendarPage
    :top-classes: ls.joyous.models.calendar.CalendarPage
    :parts: 1
.. autoclass:: GeneralCalendarPage
    :show-inheritance:

    .. automethod:: _allowAnotherAt
    .. automethod:: _getEventsByDay
    .. automethod:: _getEventsByWeek
    .. automethod:: _getUpcomingEvents
    .. automethod:: _getPastEvents
    .. automethod:: _getEventFromUid
    .. automethod:: _getAllEvents
