(function() {
  ({
    "version": 3,
    "names": [],
    "mappings": "",
    "sources": ["minicalendar.coffee"],
    "sourcesContent": ["#---------------------------------------------------------------------------\n# MiniCalendar scripts\n#---------------------------------------------------------------------------\n\nclass @MiniCalendar\n    constructor: (@calendarUrl, @year, @month) ->\n        return\n\n    enable: () ->\n        $(\"a.minicalPrev\").click =>\n            @month--\n            if @month == 0\n                @month = 12\n                @year--\n            minicalUrl = \"" + this.calendarUrl + "mini/" + this.year + "/" + this.month + "\"\n            $.get(minicalUrl, @_replace.bind(@))\n\n        $(\"a.minicalNext\").click =>\n            @month++\n            if @month == 13\n                @month = 1\n                @year++\n            minicalUrl = \"" + this.calendarUrl + "mini/" + this.year + "/" + this.month + "\"\n            $.get(minicalUrl, @_replace.bind(@))\n        return\n\n    _replace: (data) ->\n        # is this is more secure than $(data) ???\n        data = $(\"<div>\").append($.parseHTML($.trim(data)))\n\n        heading = $(\"table.minicalendar thead .month-heading\")\n        heading.find(\".month-name\").replaceWith(data.find(\".month-name\"))\n        heading.find(\".year-number\").replaceWith(data.find(\".year-number\"))\n        tbody = $(\"table.minicalendar tbody\")\n        tbody.replaceWith(data.find(\"tbody\"))\n\n\n\n"],
    "file": "../minicalendar.coffee"
  });

}).call(this);
