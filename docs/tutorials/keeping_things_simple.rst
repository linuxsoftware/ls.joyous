Keeping things simple
=====================

Timezones? Views? Groups? Multiday-recurring events?  All you wanted was a
simple calendar of local one-off events!  This tutorial will show you how
to hide unneeded features to give your users a more streamlined interface.

In this example we will create a calendar for the gigs our band is playing.

0.  Install Wagtail and Joyous.  (See the :doc:`previous tutorial <out_of_the_box>`
    for details on that.)


1.  Create an application to hold the customisations we are going to make.

    .. code-block:: console

        $ ./manage.py startapp gigs

2.  Add this application to your INSTALLED_APPS setting
    in mysite/mysite/settings/base.py

    .. code-block:: python

        INSTALLED_APPS = [
            ...
            'gigs',
            ...
        ]

3.  Edit gigs/models.py to have

    .. code-block:: python

        from ls.joyous.models import (MultidayEventPage, RecurringEventPage,
                                      MultidayRecurringEventPage, removeContentPanels)

        # Hide unwanted event types
        MultidayEventPage.is_creatable = False
        RecurringEventPage.is_creatable = False
        MultidayRecurringEventPage.is_creatable = False

        # Hide unwanted content
        removeContentPanels(["category", "tz", "group_page", "website"])

4.  Start your server

    .. code-block:: console

        $ ./manage.py runserver

    And, point your web browser at ``http://localhost:8000/admin/``.


5.  Select Home | Add child page, and add a ``Calendar page``.  
    (Or if you already have, select Edit for it.)

6.  Give the calendar a suitable ``Title`` etc.

7.  Select the Settings tab.  Under VIEW OPTIONS | View choices
    untick the List View and Weekly View options.

   .. figure:: ../_static/img/tutorials/kts/calendar_view_choices.png
      :alt: Gigs Calendar

8.  Publish this.

9.  Add a child-page to your calendar.  Notice how there is no need to
    select the event type, it goes straight to creating a new simple
    Event page.

   .. figure:: ../_static/img/tutorials/kts/event_page_new.png
      :alt: NEW Event page

10. Add a ``Title``, ``Date`` and some ``Details``.  
    Notice how the user is not prompted for the fields 
    Category, TZ, Group page, or Website due to the call to
    ``removeContentPanels`` in gigs/models.py.

        
11. Publish your event.  View the calendar again. Your event will be displayed
    on the date you set for it.

    .. figure:: ../_static/img/tutorials/kts/calendar_20191102_0.png
        :alt: Gigs Calendar

    Notice that the links for List View and Weekly View are not shown.

Hopefully your users will find this interface easy to use.
