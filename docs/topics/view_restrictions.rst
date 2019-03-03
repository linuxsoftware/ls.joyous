View Restrictions
=================

Just like other Wagtail pages Joyous event pages can be made :doc:`private <wagtail:advanced_topics/privacy>`.

When an event is private and you do not have authority to view it, it will not show up on the calendar or in any list of events.  But, if it is a Cancellation or Postponement it will still have an effect upon its parent RecurringEvent.  E.g. If an event that occurs weekly is postponed for this week, BUT the postponement is hidden from you, then you will see there is not an occurrence of that event this week, but you will not see why.  [I can't imagine why anyone would want to hide the postponement, but not the recurring event - but if they do, this is the design decision Joyous implements.]

For password protected events: "authority to view" means you have viewed that page by entering the correct password once in this login-session already.  Joyous is not going to prompt for passwords itself.

When exporting if the user has publish rights (includes the rights to change the view restriction) to the event then it will be exported, otherwise it'll be based upon their view rights.

