#---------------------------------------------------------------------------
# MiniCalendar scripts
#---------------------------------------------------------------------------

# delay choosing jQuery variable until constructor
root = @
$ = undefined

class @MiniCalendar
    constructor: (@calendarUrl, @year, @month) ->
        $ = root.joyJQ ? root.$

    enable: () ->
        $(".joy-minical__prev").click =>
            @month--
            if @month == 0
                @month = 12
                @year--
            minicalUrl = "#{@calendarUrl}mini/#{@year}/#{@month}/"
            $.get(minicalUrl, @_replace.bind(@))
            return
        $(".joy-minical__next").click =>
            @month++
            if @month == 13
                @month = 1
                @year++
            minicalUrl = "#{@calendarUrl}mini/#{@year}/#{@month}/"
            $.get(minicalUrl, @_replace.bind(@))
            return
        return

    _replace: (data) ->
        data = $("<div>").append($.parseHTML($.trim(data)))
        month = $(".joy-minical__month-name")
        month.replaceWith(data.find(".joy-minical__month-name"))
        year = $(".joy-minical__year-number")
        year.replaceWith(data.find(".joy-minical__year-number"))
        tbody = $(".joy-minical__body")
        tbody.replaceWith(data.find(".joy-minical__body"))
        return
