(function() {
  this.MiniCalendar = (function() {
    function MiniCalendar(calendarUrl, year, month) {
      this.calendarUrl = calendarUrl;
      this.year = year;
      this.month = month;
      return;
    }

    MiniCalendar.prototype.enable = function() {
      $("a.minicalPrev").click((function(_this) {
        return function() {
          var minicalUrl;
          _this.month--;
          if (_this.month === 0) {
            _this.month = 12;
            _this.year--;
          }
          minicalUrl = _this.calendarUrl + "mini/" + _this.year + "/" + _this.month;
          return $.get(minicalUrl, _this._replace.bind(_this));
        };
      })(this));
      $("a.minicalNext").click((function(_this) {
        return function() {
          var minicalUrl;
          _this.month++;
          if (_this.month === 13) {
            _this.month = 1;
            _this.year++;
          }
          minicalUrl = _this.calendarUrl + "mini/" + _this.year + "/" + _this.month;
          return $.get(minicalUrl, _this._replace.bind(_this));
        };
      })(this));
    };

    MiniCalendar.prototype._replace = function(data) {
      var heading, tbody;
      data = $("<div>").append($.parseHTML($.trim(data)));
      heading = $("table.minicalendar thead .month-heading");
      heading.find(".month-name").replaceWith(data.find(".month-name"));
      heading.find(".year-number").replaceWith(data.find(".year-number"));
      tbody = $("table.minicalendar tbody");
      return tbody.replaceWith(data.find("tbody"));
    };

    return MiniCalendar;

  })();

}).call(this);
