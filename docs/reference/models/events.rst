Events
======

.. automodule:: ls.joyous.models

Get Events API
--------------
.. autofunction:: getAllEventsByDay

.. autofunction:: getAllEventsByWeek

.. autofunction:: getAllUpcomingEvents

.. autofunction:: getAllPastEvents

.. autofunction:: getGroupUpcomingEvents

.. autofunction:: getEventFromUid

.. autofunction:: getAllEvents

EventsOnDay
-----------
.. autoclass:: EventsOnDay

    .. attribute:: date

    .. attribute:: holiday

    .. attribute:: days_events

        The events that start on this day

        :rtype: list of the namedtuple ThisEvent (title, page, url)

    .. attribute:: continuing_events

        The events that are still continuing on this day

        :rtype: list of the namedtuple ThisEvent (title, page, url)

    .. autoattribute:: all_events
    .. autoattribute:: preview
    .. autoattribute:: weekday

EventCategory
-------------
.. inheritance-diagram:: EventCategory
    :top-classes: wagtail.models.Page
    :parts: 1
.. autoclass:: EventCategory
    :show-inheritance:

    .. attribute:: code

        A short 4 character code for the category.

    .. attribute:: name

        The category name.

EventBase
---------
.. inheritance-diagram:: EventBase
    :top-classes: django.db.models.base.Model
    :parts: 1
.. autoclass:: EventBase
    :show-inheritance:

    .. attribute:: uid

        A unique identifier for the event, used for iCal import/export.

    .. attribute:: category

        What type of event is this?

    .. attribute:: image

        A banner image for the event.

    .. attribute:: time_from

        The time the event starts (optional).

    .. attribute:: time_to

        The time the event finishes (optional).

    .. attribute:: tz

        The time zone for the event.  No, sorry, you can't set different time zones for time_from and time_to.

    .. attribute:: group_page

        A page chosen to link a group of events together.

    .. attribute:: details

        Free text for whatever else you want to say about the event.

    .. attribute:: location

        Where the event will occur.  If wagtailgmaps is installed MapFieldPanel will be used, but this is not a requirement.

    .. attribute:: website

        A website location for the event.

    .. autoattribute:: group
    .. autoattribute:: _current_datetime_from
    .. autoattribute:: _future_datetime_from
    .. autoattribute:: _past_datetime_from
    .. autoattribute:: _first_datetime_from
    .. autoattribute:: status
    .. autoattribute:: status_text
    .. autoattribute:: at
    .. automethod:: _removeContentPanels
    .. automethod:: isAuthorized
    .. automethod:: get_context
    .. automethod:: _getLocalWhen
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt
    .. automethod:: _getToDt

SimpleEventPage
---------------
.. inheritance-diagram:: SimpleEventPage
    :top-classes: wagtail.models.Page, ls.joyous.models.event_base.EventBase
    :parts: 1
.. autoclass:: SimpleEventPage
    :show-inheritance:

    .. attribute:: date

        The date that the event occurs on.

    .. autoattribute:: when
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt
    .. automethod:: _getToDt

MultidayEventPage
-----------------
.. inheritance-diagram:: MultidayEventPage
    :top-classes: wagtail.models.Page, ls.joyous.models.event_base.EventBase
    :parts: 1
.. autoclass:: MultidayEventPage
    :show-inheritance:

    .. attribute:: date_from

        The date the event starts.

    .. attribute:: date_to

        The date the event finishes.

    .. autoattribute:: when
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt
    .. automethod:: _getToDt

RecurringEventPage
------------------
.. inheritance-diagram:: RecurringEventPage
    :top-classes: wagtail.models.Page, ls.joyous.models.event_base.EventBase
    :parts: 1
.. autoclass:: RecurringEventPage
    :show-inheritance:

    .. attribute:: repeat

        The recurrence rule of when the event occurs.

    .. attribute:: num_days

        The number of days an occurrence lasts for.

    .. autoattribute:: next_date
    .. autoattribute:: _current_datetime_from
    .. autoattribute:: _future_datetime_from
    .. autoattribute:: prev_date
    .. autoattribute:: _past_datetime_from
    .. autoattribute:: _first_datetime_from
    .. autoattribute:: status
    .. autoattribute:: status_text
    .. autoattribute:: when
    .. automethod:: _getFromTime
    .. automethod:: _futureExceptions
    .. automethod:: _nextOn
    .. automethod:: _occursOn
    .. automethod:: _getMyFirstDatetimeFrom
    .. automethod:: _getMyFirstDatetimeTo
    .. automethod:: _getMyNextDate

MultidayRecurringEventPage
--------------------------
.. inheritance-diagram:: MultidayRecurringEventPage
    :top-classes: wagtail.models.Page, ls.joyous.models.recurring_events.RecurringEventPage
    :parts: 1
.. autoclass:: MultidayRecurringEventPage
    :show-inheritance:

EventExceptionBase
------------------
.. inheritance-diagram:: EventExceptionBase
    :top-classes: django.db.models.base.Model
    :parts: 1
.. autoclass:: EventExceptionBase
    :show-inheritance:

    .. attribute:: overrides

        The recurring event that we are updating. overrides is also the parent (the published version of parent), but the parent is not set until the child is saved and added.

    .. attribute:: num_days

        Shortcut for overrides.num_days.

    .. attribute:: time_from

        Shortcut for overrides.time_from.

    .. attribute:: time_to

        Shortcut for overrides.time_to.

    .. attribute:: tz

        Shortcut for overrides.tz.

    .. attribute:: group

        Shortcut for overrides.group.

    .. attribute:: category

        Shortcut for overrides.category.

    .. attribute:: image

        Shortcut for overrides.image.

    .. attribute:: location

        Shortcut for overrides.location.

    .. attribute:: website

        Shortcut for overrides.website.

    .. autoattribute:: at
    .. autoattribute:: overrides_repeat
    .. automethod:: get_context
    .. automethod:: isAuthorized
    .. automethod:: _copyFieldsFromParent

DateExceptionBase
------------------
.. inheritance-diagram:: DateExceptionBase
    :top-classes: ls.joyous.models.recurring_events.EventExceptionBase
    :parts: 1
.. autoclass:: DateExceptionBase
    :show-inheritance:

    .. attribute:: except_date

        For this date.

    .. autoattribute:: local_title
    .. autoattribute:: when
    .. automethod:: full_clean
    .. automethod:: _getLocalWhen
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt
    .. automethod:: _getToDt
    .. automethod:: _copyFieldsFromParent

ExtraInfoPage
-------------
.. inheritance-diagram:: ExtraInfoPage
    :top-classes: wagtail.models.Page, ls.joyous.models.recurring_events.DateExceptionBase
    :parts: 1
.. autoclass:: ExtraInfoPage
    :show-inheritance:

    .. attribute:: extra_title

        A more specific title for this occurrence (optional).

    .. attribute:: extra_information

        Information just for this date.

    .. attribute:: details

        Shortcut for overrides.details.

    .. autoattribute:: status
    .. autoattribute:: status_text
    .. autoattribute:: _current_datetime_from
    .. autoattribute:: _future_datetime_from
    .. autoattribute:: _past_datetime_from

CancellationBase
----------------
.. inheritance-diagram:: CancellationBase
    :top-classes: django.db.models.base.Model
    :parts: 1
.. autoclass:: CancellationBase
    :show-inheritance:

    .. attribute:: cancellation_title

        Show in place of cancelled event (Leave empty to show nothing).

    .. attribute:: cancellation_details

        Why was the event cancelled?

    .. autoattribute:: status
    .. autoattribute:: status_text

CancellationPage
----------------
.. inheritance-diagram:: CancellationPage
    :top-classes: wagtail.models.Page, ls.joyous.models.recurring_events.DateExceptionBase, ls.joyous.models.recurring_events.CancellationBase
    :parts: 1
.. autoclass:: CancellationPage
    :show-inheritance:

    .. autoattribute:: _current_datetime_from
    .. autoattribute:: _future_datetime_from
    .. autoattribute:: _past_datetime_from
    .. automethod:: getCancellationUrl
    .. autoattribute:: cancellation_url

RescheduleEventBase
-------------------
.. inheritance-diagram:: RescheduleEventBase
    :top-classes: ls.joyous.models.event_base.EventBase
    :parts: 1
.. autoclass:: RescheduleEventBase
    :show-inheritance:

    .. attribute:: num_days

        The number of days an occurrence lasts for.

    .. attribute:: tz

        Shortcut for overrides.tz.

    .. attribute:: group

        Shortcut for overrides.group.

    .. attribute:: uid

        Shortcut for overrides.uid.

    .. automethod:: get_context

PostponementPage
----------------
.. inheritance-diagram:: PostponementPage
    :top-classes: ls.joyous.models.recurring_events.CancellationPage, ls.joyous.models.recurring_events.RescheduleEventBase
    :parts: 1
.. autoclass:: PostponementPage
    :show-inheritance:

    .. attribute:: postponement_title 

        The title for the postponed event.

    .. attribute:: date

        The date that the event was postponed to.

    .. autoattribute:: status
    .. autoattribute:: when
    .. autoattribute:: postponed_from_when
    .. autoattribute:: what
    .. autoattribute:: postponed_from
    .. autoattribute:: postponed_to
    .. autoattribute:: at
    .. automethod:: serveCancellation
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt
    .. automethod:: _getToDt
    .. automethod:: _copyFieldsFromParent

RescheduleMultidayEventPage
---------------------------
.. inheritance-diagram:: RescheduleMultidayEventPage
    :top-classes: ls.joyous.models.recurring_events.PostponementPage
    :parts: 1
.. autoclass:: RescheduleMultidayEventPage
    :show-inheritance:

ClosedForHolidaysPage
---------------------
.. inheritance-diagram:: ClosedForHolidaysPage
    :top-classes: wagtail.models.Page, ls.joyous.models.recurring_events.EventExceptionBase, ls.joyous.models.recurring_events.CancellationBase
    :parts: 1
.. autoclass:: ClosedForHolidaysPage
    :show-inheritance:

    .. attribute:: all_holidays

        Closed for all holidays?

    .. attribute:: closed_for

        Or, closed for these holidays

    .. autoattribute:: local_title
    .. autoattribute:: when
    .. autoattribute:: closed
    .. autoattribute:: _current_datetime_from
    .. autoattribute:: _future_datetime_from
    .. autoattribute:: _past_datetime_from
    .. autoattribute:: _closed_for_dates
    .. automethod:: can_create_at
    .. automethod:: _getMyDates
    .. automethod:: _getFromTime
    .. automethod:: _cacheClosedSet
    .. automethod:: _closedOn

ExtCancellationPage
-------------------
.. inheritance-diagram:: ExtCancellationPage
    :top-classes: wagtail.models.Page, ls.joyous.models.recurring_events.EventExceptionBase, ls.joyous.models.recurring_events.CancellationBase
    :parts: 1
.. autoclass:: ExtCancellationPage
    :show-inheritance:

    .. attribute:: cancelled_from_date

        Cancelled from this date

    .. attribute:: cancelled_to_date

        Cancelled to this date (Leave empty for "until further notice")

    .. autoattribute:: local_title
    .. autoattribute:: until_when
    .. autoattribute:: when
    .. autoattribute:: _current_datetime_from
    .. autoattribute:: _future_datetime_from
    .. autoattribute:: _past_datetime_from
    .. automethod:: full_clean
    .. automethod:: _getMyDates
    .. automethod:: _getMyRawDates
    .. automethod:: _getFromTime
    .. automethod:: _closedOn
