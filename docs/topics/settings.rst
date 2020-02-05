Settings
========

.. setting:: JOYOUS_DATE_FORMAT

``JOYOUS_DATE_FORMAT``
----------------------

Default: Falls back to Django date formatting.
(See :doc:`django:topics/i18n/formatting`, :setting:`django:DATE_FORMAT`)

Format of dates, if different from the Django standard.  Uses the same options as :ref:`django:date-and-time-formatting-specifiers`, plus 'X' which only gives the year if it is not the current year.

Added in :doc:`version 0.9.1 </releases/0.9.1>`.  Use ``JOYOUS_DATE_FORMAT = "l jS \\o\\f F X"`` for formatting as it was previously.


.. setting:: JOYOUS_DATE_SHORT_FORMAT

``JOYOUS_DATE_SHORT_FORMAT``
---------------------------------

Default: Falls back to Django date formatting.
(See :doc:`django:topics/i18n/formatting`, :setting:`django:SHORT_DATE_FORMAT`)

Short format of dates, if different from the Django standard.  Uses the same options as :setting:`JOYOUS_DATE_FORMAT`.

Added in :doc:`version 0.9.1 </releases/0.9.1>`.  Use ``JOYOUS_DATE_SHORT_FORMAT = "j F Y"`` for formatting as it was previously.


.. setting:: JOYOUS_FIRST_DAY_OF_WEEK

``JOYOUS_FIRST_DAY_OF_WEEK``
---------------------------------

Default: Falls back to Django date formatting.
(See :doc:`django:topics/i18n/formatting`, :setting:`django:FIRST_DAY_OF_WEEK`)

The first day of the week, 0=Sunday or 1=Monday.  

Added in :doc:`version 0.9.5 </releases/0.9.5>`.

.. setting:: JOYOUS_EVENTS_PER_PAGE

``JOYOUS_EVENTS_PER_PAGE``
---------------------------------

Default: ``25``

Page limit for a list of events.

Added in :doc:`version 0.8.1 </releases/0.8.1>`.


.. setting:: JOYOUS_GROUP_MODEL

``JOYOUS_GROUP_MODEL``
---------------------------------

Default: ``"joyous.GroupPage"``

To swap out the :doc:`/topics/groups` model.


.. setting:: JOYOUS_GROUP_SELECTABLE

``JOYOUS_GROUP_SELECTABLE``
---------------------------------

Default: ``False``

Enable group selection? ``False`` or ``True``.


.. setting:: JOYOUS_HOLIDAYS

``JOYOUS_HOLIDAYS``
---------------------------------

Default: ``""`` (Empty string)

Observed holidays using
`python-holidays <https://github.com/dr-prodigy/python-holidays>`_.
Specified as  string of countries [with regions in square brackets] separated by commas.
e.g. ``"NZ[WTL,Nelson],AU[*],Northern Ireland"``.

See :ref:`calendarholidays`.


.. setting:: JOYOUS_RSS_FEED_IMAGE

``JOYOUS_RSS_FEED_IMAGE``
---------------------------------

Default: ``"/static/joyous/img/logo.png"``

This is the image that is displayed on RSS for your channel.


.. setting:: JOYOUS_THEME_CSS


``JOYOUS_THEME_CSS``
---------------------------------

Default: ``""`` (Empty string)

The path of a theme CSS file to include.  
Joyous CSS does not push colour or font choices.  But there are theme CSS files 
available which you can optionally choose to import using this setting.

Available themes:
 * ``joyous_coast_theme.css``: Greys and gold.
 * ``joyous_forest_theme.css``: Greens.
 * ``joyous_stellar_theme.css``: A dark background theme.

Added in :doc:`version 0.9.0 </releases/0.9.0>`.  Use
``JOYOUS_THEME_CSS = "/static/joyous/css/joyous_coast_theme.css"``
to continue with the previous default appearance.


.. setting:: JOYOUS_TIME_FORMAT

``JOYOUS_TIME_FORMAT``
---------------------------------

Default: Falls back to Django time formatting.
(See :doc:`django:topics/i18n/formatting`, :setting:`django:TIME_FORMAT`)

Format of times, if different from the Django standard.   Uses the same options as :ref:`django:date-and-time-formatting-specifiers`, plus 'q' which gives am or pm in lowercase.

Added in :doc:`version 0.9.1 </releases/0.9.1>`.  Use ``JOYOUS_TIME_FORMAT = "fq"`` for formatting as it was previously.


.. setting:: JOYOUS_TIME_INPUT

``JOYOUS_TIME_INPUT``
---------------------------------

Default: ``"24"``

Prompt for 12 or 24 hour times.


.. setting:: JOYOUS_UPCOMING_INCLUDES_STARTED

``JOYOUS_UPCOMING_INCLUDES_STARTED``
------------------------------------

Default: ``False``

If this is set to ``True`` then the list of upcoming events will also include
events that have already started but have not yet finished.

Added in :doc:`version 0.9.5 </releases/0.9.5>`.
