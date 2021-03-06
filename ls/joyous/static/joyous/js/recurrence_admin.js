// Generated by CoffeeScript 1.10.0
(function() {
  var $, RecurrenceWidget, ref, ref1;

  $ = (ref = (ref1 = this.joyJQ) != null ? ref1 : this.$) != null ? ref : django.jQuery;

  RecurrenceWidget = (function() {
    function RecurrenceWidget(widgetId) {
      var ourDiv;
      ourDiv = $("#" + widgetId);
      this.our = ourDiv.find.bind(ourDiv);
      this._init();
      return;
    }

    RecurrenceWidget.prototype._init = function() {
      var freq, showAdvanced;
      showAdvanced = this._hasAdvanced();
      this.our(".joy-rr__show-advanced-cbx").prop("checked", showAdvanced);
      this.our(".joy-rr__advanced-repeat").toggle(showAdvanced);
      freq = this.our(".joy-rr__freq-choice > select").val();
      this._freqChanged(freq);
      this._primaryOrdDayChanged();
    };

    RecurrenceWidget.prototype._hasAdvanced = function() {
      var dayChoice, dtstart, interval, month, monthsTicked, ordChoice, secondaryOrdDaySet, weekday, weekdaysTicked;
      interval = this.our(".joy-rr__interval-num > input").val();
      if (interval && parseInt(interval, 10) > 1) {
        return true;
      }
      weekdaysTicked = this.our(".joy-rr__weekdays :checkbox:checked").map(function() {
        return this.value;
      }).get();
      if (weekdaysTicked.length > 1) {
        return true;
      }
      dtstart = new Date(this.our(".joy-rr__start-date > input").val());
      weekday = (dtstart.getDay() + 6) % 7;
      if (weekdaysTicked.length === 1 && parseInt(weekdaysTicked[0], 10) !== weekday) {
        return true;
      }
      month = dtstart.getMonth() + 1;
      monthsTicked = this.our(".joy-rr__months :checkbox:checked").map(function() {
        return this.value;
      }).get();
      if (monthsTicked.length > 1) {
        return true;
      }
      if (monthsTicked.length === 1 && parseInt(monthsTicked[0], 10) !== month) {
        return true;
      }
      ordChoice = this.our(".joy-rr__primary .joy-rr__ord-choice > select").val();
      if (parseInt(ordChoice, 10) !== 101) {
        return true;
      }
      dayChoice = this.our(".joy-rr__primary .joy-rr__day-choice > select").val();
      if (parseInt(dayChoice, 10) !== 200) {
        return true;
      }
      secondaryOrdDaySet = $(".joy-rr__secondary select").is(function() {
        return $(this).val() !== "";
      });
      if (secondaryOrdDaySet) {
        return true;
      }
      return false;
    };

    RecurrenceWidget.prototype._clearAdvanced = function() {
      var dtstart, weekday;
      this.our(".joy-rr__interval-num > input").val(1);
      this.our(".joy-rr__weekdays :checkbox").prop("checked", false);
      this.our(".joy-rr__months :checkbox").prop("checked", false);
      dtstart = new Date(this.our(".joy-rr__start-date > input").val());
      weekday = (dtstart.getDay() + 6) % 7;
      this.our(".joy-rr__weekdays :checkbox[value=" + weekday + "]").prop("checked", true);
      this.our(".joy-rr__primary .joy-rr__ord-choice > select").val(101);
      this.our(".joy-rr__primary .joy-rr__day-choice > select").val(200);
      this.our(".joy-rr__secondary select").val("").prop('disabled', true);
    };

    RecurrenceWidget.prototype.enable = function() {
      this._enableShowAdvanced();
      this._enableStartDateChange();
      this._enableFreqChange();
      this._enableSecondaryOrdDayClear();
      this._enablePrimaryOrdDayChange();
    };

    RecurrenceWidget.prototype._enableShowAdvanced = function() {
      this.our(".joy-rr__show-advanced-cbx").click((function(_this) {
        return function(ev) {
          if ($(ev.target).prop("checked")) {
            _this.our(".joy-rr__advanced-repeat").show();
          } else {
            _this.our(".joy-rr__advanced-repeat").hide();
            _this._clearAdvanced();
          }
          return true;
        };
      })(this));
    };

    RecurrenceWidget.prototype._enableStartDateChange = function() {
      this.our(".joy-rr__start-date > input").change((function(_this) {
        return function(ev) {
          var showAdvanced;
          showAdvanced = _this.our(".joy-rr__show-advanced-cbx").prop("checked");
          if (!showAdvanced) {
            _this._clearAdvanced();
          }
          return false;
        };
      })(this));
    };

    RecurrenceWidget.prototype._enableFreqChange = function() {
      this.our(".joy-rr__freq-choice > select").change((function(_this) {
        return function(ev) {
          _this._freqChanged($(ev.target).val());
          _this._clearAdvanced();
          return false;
        };
      })(this));
    };

    RecurrenceWidget.prototype._enableSecondaryOrdDayClear = function() {
      this.our(".joy-rr__secondary .joy-rr__ord-choice > select").change((function(_this) {
        return function(ev) {
          var row;
          if ($(ev.target).find("option:selected").val() === "") {
            row = $(ev.target).closest(".joy-rr__double-field");
            row.find(".joy-rr__day-choice > select").val("");
          }
          return false;
        };
      })(this));
      this.our(".joy-rr__secondary .joy-rr__day-choice > select").change((function(_this) {
        return function(ev) {
          var row;
          if ($(ev.target).find("option:selected").val() === "") {
            row = $(ev.target).closest(".joy-rr__double-field");
            row.find(".joy-rr__ord-choice > select").val("");
          }
          return false;
        };
      })(this));
    };

    RecurrenceWidget.prototype._enablePrimaryOrdDayChange = function() {
      this.our(".joy-rr__primary select").change((function(_this) {
        return function(ev) {
          _this._primaryOrdDayChanged();
          return false;
        };
      })(this));
    };

    RecurrenceWidget.prototype._primaryOrdDayChanged = function() {
      var day, ord, ref2, ref3;
      ord = this.our(".joy-rr__primary .joy-rr__ord-choice option:selected").val();
      day = this.our(".joy-rr__primary .joy-rr__day-choice option:selected").val();
      if ((-1 <= (ref2 = parseInt(ord, 10)) && ref2 <= 5) && (0 <= (ref3 = parseInt(day, 10)) && ref3 <= 6)) {
        this.our(".joy-rr__secondary select").prop('disabled', false);
      } else {
        this.our(".joy-rr__secondary select").val("").prop('disabled', true);
      }
    };

    RecurrenceWidget.prototype._freqChanged = function(freq) {
      var frequency, visible;
      visible = [false, false, false];
      frequency = parseInt(freq, 10);
      switch (frequency) {
        case 3:
          visible = [false, false, false];
          break;
        case 2:
          visible = [true, false, false];
          break;
        case 1:
          visible = [false, true, false];
          break;
        case 0:
          visible = [false, true, true];
      }
      this.our(".joy-rr__advanced-weekly-repeat").toggle(visible[0]);
      this.our(".joy-rr__advanced-monthly-repeat").toggle(visible[1]);
      this.our(".joy-rr__advanced-yearly-repeat").toggle(visible[2]);
      this.our(".joy-rr__interval-units-days").toggle(frequency === 3);
      this.our(".joy-rr__interval-units-weeks").toggle(frequency === 2);
      this.our(".joy-rr__interval-units-months").toggle(frequency === 1);
      this.our(".joy-rr__interval-units-years").toggle(frequency === 0);
    };

    return RecurrenceWidget;

  })();

  this.initRecurrenceWidget = function(id) {
    var widget;
    widget = new RecurrenceWidget(id);
    widget.enable();
  };

  this.initExceptionDateChooser = function(id, validDates, opts) {
    var dtpOpts;
    dtpOpts = {
      onGenerate: function(ct) {
        var dd, future, i, len, mm, past, results, yyyy, yyyymmdd;
        past = new Date();
        past.setDate(past.getDate() - 200);
        past.setDate(1);
        future = new Date();
        future.setDate(future.getDate() + 600);
        future.setDate(1);
        if (validDates !== null && (past < ct && ct < future)) {
          $(this).find('td.xdsoft_date').addClass('xdsoft_disabled');
          results = [];
          for (i = 0, len = validDates.length; i < len; i++) {
            yyyymmdd = validDates[i];
            yyyy = parseInt(yyyymmdd.slice(0, 4), 10);
            mm = parseInt(yyyymmdd.slice(4, 6), 10) - 1;
            dd = parseInt(yyyymmdd.slice(6, 8), 10);
            results.push($(this).find("td.xdsoft_date[data-year=" + yyyy + "][data-month=" + mm + "][data-date=" + dd + "]").removeClass('xdsoft_disabled'));
          }
          return results;
        }
      },
      closeOnDateSelect: true,
      timepicker: false,
      scrollInput: false,
      format: 'Y-m-d',
      dayOfWeekStart: 0
    };
    $.extend(dtpOpts, opts);
    return $('#' + id).datetimepicker(dtpOpts);
  };

}).call(this);
