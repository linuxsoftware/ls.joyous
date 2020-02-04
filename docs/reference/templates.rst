=========
Templates
=========

Hierarchy
=========
.. graphviz::

   digraph  {
      rankdir=LR;
      node [shape=box];
      "joyous_base" -> "calendar_base" -> "calendar_list_base" -> "calendar_list_upcoming";
      "calendar_list_base" -> "calendar_list_past";
      "calendar_list_base" -> "calendar_list_day";
      "calendar_base" -> "calendar_table_base" -> "calendar_month";
      "calendar_table_base" -> "calendar_week";
      "joyous_base" -> "event_base";
      "event_base" -> "simple_event_page";
      "event_base" -> "multiday_event_page";
      "event_base" -> "recurring_event_page";
      "event_base" -> "exception_base" -> "extra_info_page";
      "exception_base" -> "cancellation_page";
      "exception_base" -> "postponement_page";
      "exception_base" -> "postponement_page_from";
      "joyous_base" -> "group_page";
   }

Templates
=========

joyous/joyous_base.html
-------------------------

**Extends** : base.html

The blocks **content**, **extra_css** and **extra_js** are required in the base.html template for the Joyous templates to work.  A Wagtail project based upon the `default template <https://github.com/wagtail/wagtail/blob/master/wagtail/project_template/project_name/templates/base.html>`_ will have these.

Blocks
~~~~~~
* **body_class**
* **extra_css**
* **content**
* **extra_js**


joyous/calendar_base.html
-------------------------

**Extends** : joyous/joyous_base.html

Blocks
~~~~~~
* **content**

  * **cal_all**

    * **cal_intro**
    * **view_choices**
    * **cal_subtitle**
    * **cal_events**
    * **cal_footer**


joyous/calendar_list_base.html
------------------------------

**Extends** : joyous/calendar_base.html

Blocks
~~~~~~
* **cal_events**

  * **cal_view_class**
  * **event_item**
  * **events_pagination**

Includes
~~~~~~~~
* joyous/includes/event_item.html


joyous/calendar_list_upcoming.html
----------------------------------

**Extends** : joyous/calendar_list_base.html

Blocks
~~~~~~
* **view_choices**
* **cal_view_class**
* **cal_subtitle**
* **cal_footer**

Includes
~~~~~~~~
* joyous/includes/events_view_choices.html


joyous/calendar_list_past.html
------------------------------

**Extends** : joyous/calendar_list_base.html

Blocks
~~~~~~
* **view_choices**
* **cal_view_class**
* **cal_subtitle**

Includes
~~~~~~~~
* joyous/includes/events_view_choices.html


joyous/calendar_list_day.html
-----------------------------

**Extends** : joyous/calendar_list_base.html

Blocks
~~~~~~
* **view_choices**
* **cal_view_class**
* **cal_subtitle**

Includes
~~~~~~~~
* joyous/includes/event_item.html


joyous/calendar_table_base.html
-------------------------------

**Extends** : joyous/calendar_base.html

Blocks
~~~~~~
* **cal_events**

  * **cal_view_class**
  * **cal_thead**

    * **cal_heading**
    * **cal_weekday**

  * **cal_tbody**

    * **cal_week**

      * **cal_day**

        * **cal_day_title**
        * **days_events**

* **extra_js**

Includes
~~~~~~~~
* joyous/includes/events_view_choices.html
* joyous/includes/joyjq.html


joyous/calendar_month.html
--------------------------

**Extends** : joyous/calendar_table_base.html

Blocks
~~~~~~
* **view_choices**
* **cal_view_class**
* **cal_heading**
* **cal_day_title**

Includes
~~~~~~~~
* joyous/includes/events_view_choices.html


joyous/calendar_week.html
-------------------------

**Extends** : joyous/calendar_table_base.html

Blocks
~~~~~~
* **view_choices**
* **cal_view_class**
* **cal_heading**
* **cal_day_title**

Includes
~~~~~~~~
* joyous/includes/events_view_choices.html


joyous/event_base.html
-------------------------

**Extends** : joyous/joyous_base.html

Blocks
~~~~~~
* **content**

  * **event_status**
  * **event_title**
  * **event_image**
  * **event_who**
  * **event_when**
  * **event_where**
  * **event_details**
  * **event_footer**

Includes
~~~~~~~~
* joyous/includes/who.html
* joyous/includes/when.html
* joyous/includes/where.html


joyous/simple_event_page.html
-----------------------------

**Extends** : joyous/event_base.html


joyous/multiday_event_page.html
-------------------------------

**Extends** : joyous/event_base.html


joyous/recurring_event_page.html
--------------------------------

**Extends** : joyous/event_base.html

Blocks
~~~~~~
* **event_footer**


joyous/exception_base.html
--------------------------

**Extends** : joyous/event_base.html

Blocks
~~~~~~
* **event_footer**


joyous/extra_info_page.html
---------------------------

**Extends** : joyous/exception_base.html

Blocks
~~~~~~
* **event_title**
* **event_details**


joyous/cancellation_page.html
-----------------------------

**Extends** : joyous/exception_base.html

Blocks
~~~~~~
* **event_title**
* **event_details**


joyous/postponement_page.html
-----------------------------

**Extends** : joyous/exception_base.html

Blocks
~~~~~~
* **event_title**
* **event_details**


joyous/postponement_page_from.html
-----------------------------

**Extends** : joyous/exception_base.html

Blocks
~~~~~~
* **event_status**
* **event_title**
* **event_when**
* **event_image**
* **event_details**


joyous/group_page.html
-------------------------

**Extends** : joyous/joyous_base.html

Blocks
~~~~~~
* **content**


