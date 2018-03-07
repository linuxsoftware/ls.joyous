#---------------------------------------------------------------------------
# MiniCalendar scripts
#---------------------------------------------------------------------------

class @MiniCalendar
    constructor: (@calendarUrl, @year, @month) ->
        return

    enable: () ->
        $("a.minicalPrev").click =>
            @month--
            if @month == 0
                @month = 12
                @year--
            minicalUrl = "#{@calendarUrl}mini/#{@year}/#{@month}"
            $.get(minicalUrl, @_replace.bind(@))

        $("a.minicalNext").click =>
            @month++
            if @month == 13
                @month = 1
                @year++
            minicalUrl = "#{@calendarUrl}mini/#{@year}/#{@month}"
            $.get(minicalUrl, @_replace.bind(@))
        return

    _replace: (data) ->
        # is this is more secure than $(data) ???
        data = $("<div>").append($.parseHTML($.trim(data)))

        heading = $("table.minicalendar thead .month-heading")
        heading.find(".month-name").replaceWith(data.find(".month-name"))
        heading.find(".year-number").replaceWith(data.find(".year-number"))
        tbody = $("table.minicalendar tbody")
        tbody.replaceWith(data.find("tbody"))



