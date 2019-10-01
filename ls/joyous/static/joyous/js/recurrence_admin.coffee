#---------------------------------------------------------------------------
# Recurrence Widget
#---------------------------------------------------------------------------
$ = @joyJQ ? @$ ? django.jQuery

class RecurrenceWidget
    constructor: (widgetId) ->
        ourDiv = $("##{widgetId}")
        @our = ourDiv.find.bind(ourDiv)
        @_init()
        return

    _init: () ->
        showAdvanced = @_hasAdvanced()
        @our(".joy-rr__show-advanced-cbx").prop("checked", showAdvanced)
        @our(".joy-rr__advanced-repeat").toggle(showAdvanced)
        freq = @our(".joy-rr__freq-choice > select").val()
        @_freqChanged(freq)
        @_primaryOrdDayChanged()
        return

    _hasAdvanced: () ->
        interval = @our(".joy-rr__interval-num > input").val()
        if interval and parseInt(interval, 10) > 1
            return true

        weekdaysTicked = @our(".joy-rr__weekdays :checkbox:checked").map ->
            return this.value
        .get()
        if weekdaysTicked.length > 1
            return true
        dtstart = new Date(@our(".joy-rr__start-date > input").val())
        weekday = (dtstart.getDay() + 6) % 7  # convert from Sun=0 to Mon=0
        if weekdaysTicked.length == 1 and parseInt(weekdaysTicked[0], 10) != weekday
            return true

        month = dtstart.getMonth() + 1
        monthsTicked = @our(".joy-rr__months :checkbox:checked").map ->
            return this.value
        .get()
        if monthsTicked.length > 1
            return true
        if monthsTicked.length == 1 and parseInt(monthsTicked[0], 10) != month
            return true

        ordChoice = @our(".joy-rr__primary .joy-rr__ord-choice > select").val()
        if parseInt(ordChoice, 10) != 101
            return true
        dayChoice = @our(".joy-rr__primary .joy-rr__day-choice > select").val()
        if parseInt(dayChoice, 10) != 200
            return true
        secondaryOrdDaySet = $(".joy-rr__secondary select").is ->
            return $(this).val() != ""
        if secondaryOrdDaySet
            return true
        return false

    _clearAdvanced: () ->
        @our(".joy-rr__interval-num > input").val(1)
        @our(".joy-rr__weekdays :checkbox").prop("checked", false)
        @our(".joy-rr__months :checkbox").prop("checked", false)
        dtstart = new Date(@our(".joy-rr__start-date > input").val())
        weekday = (dtstart.getDay() + 6) % 7  # convert from Sun=0 to Mon=0
        @our(".joy-rr__weekdays :checkbox[value=#{weekday}]").prop("checked", true)
        @our(".joy-rr__primary .joy-rr__ord-choice > select").val(101)
        @our(".joy-rr__primary .joy-rr__day-choice > select").val(200)
        @our(".joy-rr__secondary select").val("").prop('disabled', true)
        return

    enable: () ->
        @_enableShowAdvanced()
        @_enableStartDateChange()
        @_enableFreqChange()
        @_enableSecondaryOrdDayClear()
        @_enablePrimaryOrdDayChange()
        return

    _enableShowAdvanced: () ->
        @our(".joy-rr__show-advanced-cbx").click (ev) =>
            if $(ev.target).prop("checked")
                @our(".joy-rr__advanced-repeat").show()
            else
                @our(".joy-rr__advanced-repeat").hide()
                @_clearAdvanced()
            return true
        return

    _enableStartDateChange: () ->
        @our(".joy-rr__start-date > input").change (ev) =>
            showAdvanced = @our(".joy-rr__show-advanced-cbx").prop("checked")
            if not showAdvanced
                @_clearAdvanced()
            return false
        return

    _enableFreqChange: () ->
        @our(".joy-rr__freq-choice > select").change (ev) =>
            @_freqChanged($(ev.target).val())
            @_clearAdvanced()
            return false
        return

    _enableSecondaryOrdDayClear: () ->
        @our(".joy-rr__secondary .joy-rr__ord-choice > select").change (ev) =>
            if $(ev.target).find("option:selected").val() == ""
                row = $(ev.target).closest(".joy-rr__double-field")
                row.find(".joy-rr__day-choice > select").val("")
            return false
        @our(".joy-rr__secondary .joy-rr__day-choice > select").change (ev) =>
            if $(ev.target).find("option:selected").val() == ""
                row = $(ev.target).closest(".joy-rr__double-field")
                row.find(".joy-rr__ord-choice > select").val("")
            return false
        return

    _enablePrimaryOrdDayChange: () ->
        @our(".joy-rr__primary select").change (ev) =>
            @_primaryOrdDayChanged()
            return false
        return

    _primaryOrdDayChanged: () ->
        ord = @our(".joy-rr__primary .joy-rr__ord-choice option:selected").val()
        day = @our(".joy-rr__primary .joy-rr__day-choice option:selected").val()
        if -1 <= parseInt(ord, 10) <= 5 and 0 <= parseInt(day, 10) <= 6
            # enable and clauses
            @our(".joy-rr__secondary select").prop('disabled', false)
        else
            @our(".joy-rr__secondary select").val("").prop('disabled', true)

        return

    _freqChanged: (freq) ->
        visible = [false, false, false]
        frequency = parseInt(freq, 10)
        switch frequency
            when 3
                visible = [false, false, false]
            when 2
                visible = [true,  false, false]
            when 1
                visible = [false, true,  false]
            when 0
                visible = [false, true, true]
        @our(".joy-rr__advanced-weekly-repeat").toggle(visible[0])
        @our(".joy-rr__advanced-monthly-repeat").toggle(visible[1])
        @our(".joy-rr__advanced-yearly-repeat").toggle(visible[2])
        @our(".joy-rr__interval-units-days").toggle(frequency==3)
        @our(".joy-rr__interval-units-weeks").toggle(frequency==2)
        @our(".joy-rr__interval-units-months").toggle(frequency==1)
        @our(".joy-rr__interval-units-years").toggle(frequency==0)
        return

@initRecurrenceWidget = (id) ->
    widget = new RecurrenceWidget(id)
    widget.enable()
    return

@initExceptionDateChooser = (id, validDates, opts) ->
    dtpOpts =
        onGenerate: (ct) ->
            past = new Date()
            past.setDate(past.getDate()-200)
            past.setDate(1)
            future = new Date()
            future.setDate(future.getDate()+600)
            future.setDate(1)
            if validDates != null and past < ct < future
                #console.log(ct)
                $(this).find('td.xdsoft_date').addClass('xdsoft_disabled')
                for yyyymmdd in validDates
                    yyyy = parseInt(yyyymmdd[0...4], 10)
                    mm   = parseInt(yyyymmdd[4...6], 10) - 1
                    dd   = parseInt(yyyymmdd[6...8], 10)
                    $(this).find("td.xdsoft_date[data-year=#{yyyy}][data-month=#{mm}][data-date=#{dd}]")
                           .removeClass('xdsoft_disabled')
        closeOnDateSelect: true
        timepicker:        false
        scrollInput:       false
        format:            'Y-m-d'
        dayOfWeekStart:    0
    $.extend(dtpOpts, opts)
    $('#' + id).datetimepicker(dtpOpts)
