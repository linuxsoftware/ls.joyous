Calendar
========
The CalendarPage is the heart of the Joyous application.

Views
~~~~~
Users can display the calendar in a Monthly, Weekly, or List View. 
(The default view is set in the Settings tab.)

The first day of the week used, Sunday or Monday, depends upon your Django
:doc:`format localization <django:topics/i18n/formatting>` or
:setting:`django:FIRST_DAY_OF_WEEK` setting.

There are actually multiple list views

* All upcoming events
* All past events
* and a "secret" all events of a day - unless there's only one - in which case it just redirects straight to that event

URLs
~~~~
How a calendar is displayed or exported depends upon the path and query string of the URL used to access it.  Consider a calendar
with the slug /events/:

============================  ==============================================================================
/events/                      Default view of the calendar - set as a per-calendar property.
/events/month/                Monthly view.
/events/week/                 Weekly view.
/events/day/                  Day list view.
/events/upcoming/             List of upcoming events.
/events/past/                 List of past events.
/events/?view=list            Specified (list|weekly|monthly) view of the calendar.
/events/2017/                 Default view of the calendar for 2017
/events/2017/?view=weekly     Specified view for 2017.
/events/2018/Apr/             Monthly view for April 2018.
/events/2018/5/               Monthly view for May 2018.
/events/2018/W2/              Weekly view for Week 2 of 2018.
/events/2018/6/18/            Day list view for the 18th of June 2018.
/events/?format=ical          Export as an :doc:`ical` file.
/events/?format=rss           Export as a RSS feed.
============================  ==============================================================================

Models
~~~~~~

.. _CalendarPage:

CalendarPage
------------
A :class:`CalendarPage <ls.joyous.models.CalendarPage>`
displays all the events in the same Wagtail :ref:`wagtail:site-model-ref` as itself.

If that isn't what you want, then have a look at
:ref:`GeneralCalendarPage` or :ref:`SpecificCalendarPage`.


.. _GeneralCalendarPage:

GeneralCalendarPage 
-------------------
Displays all the events in the database ignoring site boundaries.
See :class:`GeneralCalendarPage <ls.joyous.models.GeneralCalendarPage>`.

GeneralCalendarPage is disabled by default.  Use ``GeneralCalendarPage.is_creatable = True`` to enable it.


.. _SpecificCalendarPage:

SpecificCalendarPage 
--------------------
Displays only those events which are children of itself.
See :class:`SpecificCalendarPage <ls.joyous.models.SpecificCalendarPage>`.

SpecificCalendarPage is disabled by default.  Use ``SpecificCalendarPage.is_creatable = True`` to enable it.

.. _DeriveYourOwn:

Derive your own
----------------
If you would like some other kind of event selection you can derive your own version of 
:class:`CalendarPage <ls.joyous.models.CalendarPage>`.

Have a look at the source-code of the CalendarPages classes if you would like some other kind of event selection.
The methods
:meth:`_getEventsOnDay <ls.joyous.models.CalendarPage._getEventsOnDay>`,
:meth:`_getEventsByDay <ls.joyous.models.CalendarPage._getEventsByDay>`,
:meth:`_getEventsByWeek <ls.joyous.models.CalendarPage._getEventsByWeek>`,
:meth:`_getUpcomingEvents <ls.joyous.models.CalendarPage._getUpcomingEvents>`, and
:meth:`_getPastEvents <ls.joyous.models.CalendarPage._getPastEvents>` determine what events are displayed.
The methods 
:meth:`_getEventFromUid <ls.joyous.models.CalendarPage._getEventFromUid>` and 
:meth:`_getAllEvents <ls.joyous.models.CalendarPage._getAllEvents>` are for import and export.

.. _CalendarHolidays:

Holidays
~~~~~~~~
:class:`Holidays <ls.joyous.holidays.Holidays>` are a property of the
:class:`CalendarPage <ls.joyous.models.CalendarPage>`.

If the :setting:`JOYOUS_HOLIDAYS` setting is set then it is used to select holidays from 
`python-holidays <https://github.com/dr-prodigy/python-holidays>`_.  But it is
also possible to add other holiday sources (e.g. from 
`workalendar <https://peopledoc.github.io/workalendar/>`_ or just a simple ``dict``)
via :meth:`register <ls.joyous.holidays.Holidays.register>`. 
And to add individual days via :meth:`add <ls.joyous.holidays.Holidays.add>`.

For example:
    .. code-block:: python

        from datetime import date
        from workalendar.america import Ontario

        CalendarPage.holidays.register(Ontario())
        CalendarPage.holidays.add(date(2019,4,29), "HAPPY HAPPY")

It would also be possible to derieve different Calendar models and give them different sets of holidays.  Holidays for CalendarPage are determined programmatically, but a derieved Calendar model could choose to change this, e.g. store the holidays in the database so that different pages of the same model could have different holidays.  

