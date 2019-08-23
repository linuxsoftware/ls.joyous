Out of the box
==============

.. ootb-tutorial:

This tutorial covers what it is like to install a Joyous calendar, with no
configuration or customisations, on a fresh Wagtail site.
 
0.  You need to have setup a Wagtail site.  Follow the Wagtail
    instructions at :doc:`wagtail:getting_started/index` if you
    haven't already.  I will assume your Wagtail site is called ``mysite``,
    replace this with your actual site name.

::

1.  Install Joyous and its dependencies:

   .. code-block:: console

       $ pip install ls.joyous

2.  Add ls.joyous and wagtail.contrib.modeladmin to your INSTALLED_APPS setting
    in mysite/mysite/settings/base.py.

    .. code-block:: python

        INSTALLED_APPS = [
            ...
            'ls.joyous',
            'wagtail.contrib.modeladmin',
            ...
        ]

3.  Run the Django manage.py commands for setting up a new application to your site.

    .. code-block:: console

        $ ./manage.py migrate
        $ ./manage.py collectstatic --no-input


4.  Now you have added the ls.joyous application to your project, start your server.

    .. code-block:: console

        $ ./manage.py runserver

    And, point your web browser at ``http://localhost:8000/admin/``.

::

5.  Select Home | Add child page, and you will see that the ``Calendar page`` is a
    new possibility.

   .. figure:: ../_static/img/tutorials/ootb/home_add_child_page.png
      :alt: Create a page in Home

6.  Go ahead and choose Calendar page. Add a ``Title`` and maybe some ``Intro``
    (introductory text).

   .. figure:: ../_static/img/tutorials/ootb/new_calendar_page.png
      :alt: New Calendar page


7.  Publish this.  Select View live, and there is our new Joyous calendar.

   .. figure:: ../_static/img/tutorials/ootb/calendar_20190308_0.png
      :alt: Our Calendar

.. note::
    There can only be one CalendarPage per Wagtail site, so if you wish to 
    repeat step 5 you will have to delete this one first.  
    (See :ref:`SpecificCalendarPage` if you do want multiple calendars.)


8.  To add an event to the calendar, add it as a child-page.
    You have the choice of four types
    (We can simplify this - covered in :doc:`keeping_things_simple`).

        * ``Event page``
        * ``Multiday event page``
        * ``Multiday recurring event page``
        * ``Recurring event page``

9.  Choose Event page.  Add a ``Title``, ``Date`` and some ``Details``.  
    The ``Time zone`` will default to your current time zone which is
    set in your Wagtail Account settings.

::
        
10. Publish your event.  View the calendar again. Your event will be displayed
    on the date you set for it.

    .. figure:: ../_static/img/tutorials/ootb/calendar_20190308_1.png
        :alt: Our Calendar

    The calendar can also be displayed in a weekly view.

    .. figure:: ../_static/img/tutorials/ootb/calendar_20190308_1_W11.png
        :alt: Our Calendar

    And as a list of upcoming events.

    .. figure:: ../_static/img/tutorials/ootb/calendar_20190308_1_upcoming.png
        :alt: Our Calendar


Probably you will want to customise the calendars and events on your site to suit your audience, but hopefully this tutorial has given you a useful introduction to Joyous.


