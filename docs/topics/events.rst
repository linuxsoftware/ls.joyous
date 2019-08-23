Events
======
Events are the building blocks of the Joyous application.

When creating a new event the user is prompted which type of event to create

* :ref:`SimpleEventPage`
* :ref:`MultidayEventPage`
* :ref:`RecurringEventPage`
* :ref:`MultidayRecurringEventPage`

All the types of events share some fields in common.

* ``Title``
* ``UID``
* ``Category``
* ``Image``
* ``Start time``
* ``Finish time``
* ``Time zone``
* ``Group page``
* ``Details``
* ``Location``

The start and finish times are optional.  If left blank start is considered as
the beginning-of-the-day, and finish is considered as the end-of-the-day.

The times and dates of an event are in a certain time zone.  This will 
default to the user's current time zone which is set in their Wagtail Account
Settings.

Models
~~~~~~

.. _SimpleEventPage:

SimpleEventPage
---------------
A simple event is one that occurs just once on some date.
See :class:`SimpleEventPage <ls.joyous.models.SimpleEventPage>`.

.. _MultidayEventPage:

MultidayEventPage
-----------------
A multiday event is one that spans several days.  Unlike the simple event it
has a start date and a finish date.
See :class:`MultidayEventPage <ls.joyous.models.MultidayEventPage>`.

An example might be a boat cruise which departs on a certain date and then returns 4 days later.

.. _RecurringEventPage:

RecurringEventPage
------------------
A recurring event has multiple occurrences repeating by a certain rule.
See :class:`RecurringEventPage <ls.joyous.models.RecurringEventPage>`.

The recurrence rule is somewhat based upon `RFC 5545 <https://tools.ietf.org/html/rfc5545>`_ RRules.  Events can occur daily, weekly, monthly, or yearly intervals, by weekday, monthday, and month.  See :class:`Recurrence <ls.joyous.utils.recurrence.Recurrence>`.

A RecurringEventPage can have child pages of its own which specify exceptions to the rule.
See :ref:`CancellationPage`, :ref:`PostponementPage`, and :ref:`ExtraInfoPage` below for more details.

.. _MultidayRecurringEventPage:

MultidayRecurringEventPage
--------------------------
This is like a recurring event, but each recurrence may last for multiple days.
See :class:`MultidayRecurringEventPage <ls.joyous.models.MultidayRecurringEventPage>`.

.. _ExtraInfoPage:

ExtraInfoPage
-------------
An :class:`ExtraInfoPage <ls.joyous.models.ExtraInfoPage>`
holds some extra details for a certain occurrence of a
recurring event.

.. _CancellationPage:

CancellationPage
----------------
A :class:`CancellationPage <ls.joyous.models.CancellationPage>`
removes a certain occurrence of a recurring event.  If given
a cancellation_title this will appear in place of the occurrence, but if not
the occurrence is just quietly removed.

.. _PostponementPage:

PostponementPage
----------------
A :class:`PostponementPage <ls.joyous.models.PostponementPage>`
both removes an occurrence and adds a replacement event.
It is a bit like a combined :ref:`CancellationPage` and :ref:`SimpleEventPage` in one.

Postponement pages have two views.  View the new details at the regular path
(e.g.  /events/bbq/2019-04-10-postponement/) and the details of the
cancellation by via the /from/ view (e.g. /events/bbq/2019-04-10-postponement/from/).

.. _RescheduleMultidayEvent:

RescheduleMultidayEventPage
---------------------------
The multiday version of the :ref:`PostponementPage`.
See :class:`RescheduleMultidayEventPage <ls.joyous.models.RescheduleMultidayEventPage>`.


What about
~~~~~~~~~~

A party that starts on 2018-12-31 at 9pm and finishes on 2019-01-01 at 2am
--------------------------------------------------------------------------
This party spans 2 days, so the most accurate way of recording it would be with a :ref:`MultidayEventPage`.

But you might not consider the party as *really* being on January 1.  (After
all who is going to turn up after midnight?)  So you could record it as a
:ref:`SimpleEventPage`, but leave the time_to field blank, or enter it as
24:59:59.  It is technically not as accurate, but it is up to you.

When a Postponement is not a postponement
-----------------------------------------
The :ref:`PostponementPage` was named with the intention that it would be used
for when an occurrence of a recurring event had to be postponed until a later
time.  But it could also be used to move the occurrence to start at an earlier
time, finish at a different time, or change some other field.

If you would like to change the name, you can do so by putting the following
bit of code in your application's models.py or wagtail_hooks.py.

    .. code-block:: python

        from ls.joyous.models import PostponementPage

        PostponementPage._meta.verbose_name = "event change"
        PostponementPage._meta.verbose_name_plural = "event changes"
        PostponementPage.slugName = "change"
