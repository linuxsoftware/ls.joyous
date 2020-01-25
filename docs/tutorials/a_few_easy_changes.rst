A few easy changes
==================

.. afec-tutorial:

It is time to customize Joyous to suit your needs.  This tutorial will show some
easy changes to make.

0.  I will assume you already have Joyous installed and a calendar added.
    (See the :doc:`first tutorial <out_of_the_box>` for details on that.)

1.  Create an application to hold the customisations we are going to make.
    (If you already have one, then you can use that and skip this step.)

    .. code-block:: console

        $ ./manage.py startapp myevents

    Add this application to your INSTALLED_APPS setting
    in mysite/mysite/settings/base.py

    .. code-block:: python

        INSTALLED_APPS = [
            ...
            'myevents',
            ...
        ]

Settings
--------

2.  To start with let's add some settings.
    These can go in mysite/mysite/settings/base.py.

    .. code-block:: python

        JOYOUS_THEME_CSS = "/static/joyous/css/joyous_forest_theme.css"
        JOYOUS_HOLIDAYS = "Scotland"
        JOYOUS_DATE_FORMAT = "l jS \\o\\f F X"
        JOYOUS_DATE_SHORT_FORMAT = "j M X"
        JOYOUS_TIME_FORMAT = "fq"
        JOYOUS_TIME_INPUT = "12"

    a.  :setting:`JOYOUS_THEME_CSS` includes a theme CSS file into each Joyous page.  You 
        could do the same thing by overriding the Joyous templates (which we will look at later), 
        but this is easier.  We've chosen the forest theme file for a green palette.

    b.  :setting:`JOYOUS_HOLIDAYS` adds holiday names onto our calendar.  We've chosen the
        holidays of ``"Scotland"``.  For the holidays of a state, province or region add it in square
        brackets after the country name, e.g. ``"Canada[NS]"``.  Multiple countries and regions
        can be listed separated by commas or by using ``*`` as a wildcard.
        See `python-holidays <https://github.com/dr-prodigy/python-holidays>`_ for all the
        countries and regions that are supported.

    c.  :setting:`JOYOUS_DATE_FORMAT` for  dates like "Monday 11th of March".  

    d.  :setting:`JOYOUS_DATE_SHORT_FORMAT` for short dates like "11 Mar".  

    e.  :setting:`JOYOUS_TIME_FORMAT` for  times like "9am".  

    f.  :setting:`JOYOUS_TIME_INPUT` allows the editor to enter times in the 12 hour format, e.g. 9am.

3.  The following Django settings are also important.  Make sure they are set to values that
    are correct for you.

    .. code-block:: python

        USE_TZ = True
        TIME_ZONE = "Europe/London"
        USE_I18N = True
        USE_L10N = True
        LANGUAGE_CODE = 'en-uk'

    a.  Joyous uses timezone-aware datetimes, so :setting:`django:USE_TZ` must be set to True.
        If it is not you will get an error like ``localtime() cannot be applied to a naive datetime``
        when trying to view a calendar.

    b.  :setting:`django:TIME_ZONE` sets the default timezone that Django uses.  Wagtail also allows
        an editor to :ref:`change their time zone <wagtail:wagtail_user_time_zones>` for the
        Wagtail admin interface using the Account Settings | Current time zone panel.

    c.  :setting:`django:USE_I18N` turns on the Django translation system.  If you only ever want
        to display English you could set it to ``False``, but you might as well set it to ``True``
        in case you ever want to display your website in another language.

    d.  :setting:`django:USE_L10N` enables Django's localized formatting of numbers and dates.
        :setting:`JOYOUS_DATE_FORMAT`, :setting:`JOYOUS_DATE_SHORT_FORMAT`, 
        :setting:`JOYOUS_TIME_FORMAT`, and :setting:`JOYOUS_FIRST_DAY_OF_WEEK`
        override Django's formatting, but if they were not set
        then Joyous dates and times would be formatted according to the current locale.
        See your django/conf/locale directory to find these format files. If
        you want, you can create your own :ref:`custom format <django:custom-format-files>`.  

    e.  :setting:`django:LANGUAGE_CODE` sets the default locale that Django will use.


4.  Start your server

    .. code-block:: console

        $ ./manage.py runserver

    And, have a look at your calendar and events.

   .. figure:: ../_static/img/tutorials/afec/calendar_20191126_0.png
      :alt: Our Calendar

   .. figure:: ../_static/img/tutorials/afec/event_20190311_0.png
      :alt: Event


Templates
---------

Now, say you don't want to display the download links, and want bigger images on your
event pages.  You can do this by :doc:`overriding <django:howto/overriding-templates>`
the Joyous templates.  And, you can use :ref:`template inheritance <django:template-inheritance>`
to override just the particular :doc:`blocks </reference/templates>` you want to change.
E.g. just override the footer.

5.  Create a ``templates/joyous`` directory in your app.

6.  Add the following files to your this directory.  This will replace the download links
    in the footers of the calendars and events.

    ``calendar_base.html``

    .. code-block:: html

        {% extends "joyous/calendar_base.html" %}
        {% block cal_footer %}{% endblock cal_footer %}

    ``calendar_list_upcoming.html``

    .. code-block:: html

        {% extends "joyous/calendar_list_upcoming.html" %}
        {% block cal_footer %}{% endblock cal_footer %}

    ``event_base.html``

    .. code-block:: html

        {% extends "joyous/event_base.html" %}
        {% block event_footer %}{% endblock event_footer %}

7.  Edit ``event_base.html`` and override the ``event_image`` block for a larger image.  
    (Don't forget that you need to load ``wagtailimages_tags`` to use the ``image`` tag.)

    ``event_base.html``

    .. code-block:: html

        {% extends "joyous/event_base.html" %}
        {% load wagtailimages_tags %}

        {% block event_footer %}{% endblock event_footer %}

        {% block event_image %}
          {% if page.image %}
          <div class="joy-img">
            {% image page.image width-500 class="joy-img__img" %}
          </div>
          {% endif %}
        {% endblock event_image %}

8.  Also ``postponement_page_from.html`` has its own definition of ``event_image`` (because it displays the image of the original event not the postponement) so, for completeness, add an override for that too.

    ``postponement_page_from.html``

    .. code-block:: html

        {% extends "joyous/postponement_page_from.html" %}
        {% load wagtailimages_tags %}

        {% block event_image %}
          {% if overrides.image %}
          <div class="joy-img">
            {% image overrides.image width-500 class="joy-img__img" %}
          </div>
          {% endif %}
        {% endblock event_image %}

9.  Have another look at your calendar and events.  Notice how the export links are gone and the images are larger.

   .. figure:: ../_static/img/tutorials/afec/event_20190311_1.png
      :alt: Event

I hope that this tutorial was useful.


