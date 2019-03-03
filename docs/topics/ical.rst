iCal
====

Import
------
iCalendar is the common calendar file format.  Google, Meetup, Facebook, Outlook, Thunderbird, etc can generate iCalendar (.ics) files for a whole calendar of events or just one event.

Importing events from an iCalendar file is done via the settings tab of editing a calendar page.  The events will be imported as the children of this page.

Steps for iCalendar import:

* Pick a calendar page, or create a new one.
* Select the settings tab
* Choose you iCalendar file 

* Select "Save Draft" and events will be imported as draft pages
* or "Publish" and events will be imported as published pages

.. note::
    Before Joyous imports an event it checks if that event already exists. 
    (the UID property is used for matching)
    If it already does then it will only be updated as a new revision if
    this is a newer version (The last-modified or timestamp property is used.)
    This avoids duplicates and unnecessary revisions 

Joyous converts events from the iCalendar file into simple, multiday or
recurring event pages as appropriate.

Export
------

Steps for iCalendar export:

Joyous can export a iCalendar file with a whole calendar of event, or just one event.

To export a single event: 

* view the event
* click the "Export ICal" link

To export a whole calendar:

* view the calendar
* click the "Export ICal" link

