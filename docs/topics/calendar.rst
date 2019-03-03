Calendar
========
The CalendarPage is the heart of the Joyous application.

Views
~~~~~
Users can display the calendar in a Monthly, Weekly, or List* View. 
(See the Settings tab)

There are actually multiple list views

* All upcoming events
* All past events
* and a "secret" all events of a day - unless there's only one - in which case it just redirects straight to that event

Models
~~~~~~

.. _CalendarPage:

CalendarPage
------------
A CalendarPage displays all the events in the same Wagtail :ref:`wagtail:site-model-ref` as itself.

If that isn't what you want, then have a look at
``GeneralCalendarPage`` or ``SpecificCalendarPage``.

.. _GeneralCalendarPage:

GeneralCalendarPage 
-------------------
Displays all the events in the database ignoring site boundaries.

.. _SpecificCalendarPage:

SpecificCalendarPage 
--------------------
Displays only those events which are children of itself.

Derive your own
----------------
If you would like some other kind of event selection you can derive your own version of ``CalendarPage``.

Have a look at the source-code of the CalendarPages classes if you would like some other kind of event selection.
The methods ``_getEventsOnDay``, ``_getEventsByDay``, ``_getEventsByWeek``, ``_getUpcomingEvents``, and ``_getPastEvents`` determine what events are displayed.  The methods ``_getEventFromUid`` and ``_getAllEvents`` are for import and export.

