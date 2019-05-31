Events
------

.. automodule:: ls.joyous.models

.. autofunction:: getAllEventsByDay

.. autofunction:: getAllEventsByWeek

.. autofunction:: getAllUpcomingEvents

.. autofunction:: getAllPastEvents

.. autofunction:: getGroupUpcomingEvents

.. autofunction:: getEventFromUid

.. autofunction:: getAllEvents

.. automodule:: ls.joyous.models.events

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

.. automodule:: ls.joyous.models

.. autoclass:: EventCategory
    :show-inheritance:

    .. attribute:: code

        A short 4 character code for the category.

    .. attribute:: name

        The category name.

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
    .. autoattribute:: _upcoming_datetime_from
    .. autoattribute:: _past_datetime_from
    .. autoattribute:: _first_datetime_from
    .. autoattribute:: status
    .. autoattribute:: status_text
    .. automethod:: _removeContentPanels
    .. automethod:: isAuthorized
    .. automethod:: _getLocalWhen
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt

.. autoclass:: SimpleEventPage
    :show-inheritance:

    .. attribute:: date

        The date that the event occurs on.

    .. autoattribute:: when
    .. autoattribute:: at
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt

.. autoclass:: MultidayEventPage
    :show-inheritance:

    .. attribute:: date_from

        The date the event starts.

    .. attribute:: date_to

        The date the event finishes.

    .. autoattribute:: when
    .. autoattribute:: at
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt

.. autoclass:: RecurringEventPage
    :show-inheritance:

    .. attribute:: repeat

        The recurrence rule of when the event occurs.

    .. attribute:: num_days

        The number of days an occurrence lasts for.

    .. autoattribute:: next_date
    .. autoattribute:: _upcoming_datetime_from
    .. autoattribute:: prev_date
    .. autoattribute:: _past_datetime_from
    .. autoattribute:: _first_datetime_from
    .. autoattribute:: status
    .. autoattribute:: status_text
    .. autoattribute:: when
    .. autoattribute:: at
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt
    .. automethod:: _futureExceptions
    .. automethod:: _nextOn
    .. automethod:: _occursOn
    .. automethod:: _getMyFirstDatetimeFrom
    .. automethod:: _getMyFirstDatetimeTo

.. autoclass:: MultidayRecurringEventPage
    :show-inheritance:

.. autoclass:: EventExceptionBase
    :show-inheritance:

    .. attribute:: overrides

        The recurring event that we are updating. overrides is also the parent (the published version of parent), but the parent is not set until the child is saved and added.

    .. attribute:: except_date

        For this date.

    .. attribute:: time_from

        Shortcut for overrides.time_from.

    .. attribute:: time_to

        Shortcut for overrides.time_to.

    .. attribute:: tz

        Shortcut for overrides.tz.

    .. attribute:: group

        Shortcut for overrides.group.

    .. autoattribute:: overrides_repeat
    .. autoattribute:: local_title
    .. autoattribute:: when
    .. autoattribute:: at
    .. automethod:: _getFromTime
    .. automethod:: full_clean
    .. automethod:: isAuthorized

.. autoclass:: ExtraInfoPage
    :show-inheritance:

    .. attribute:: extra_title

        A more specific title for this occurrence (optional).

    .. attribute:: extra_information

        Information just for this date.

    .. autoattribute:: status
    .. autoattribute:: status_text
    .. autoattribute:: _upcoming_datetime_from
    .. autoattribute:: _past_datetime_from

.. autoclass:: CancellationPage
    :show-inheritance:

    .. attribute:: cancellation_title

        Show in place of cancelled event (Leave empty to show nothing).

    .. attribute:: cancellation_information

        Why was the event cancelled?

    .. autoattribute:: status
    .. autoattribute:: status_text

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
    .. automethod:: _getFromTime
    .. automethod:: _getFromDt

.. autoclass:: RescheduleMultidayEventPage
    :show-inheritance:

