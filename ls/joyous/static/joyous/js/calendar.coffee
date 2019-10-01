#---------------------------------------------------------------------------
# Calendar scripts
#---------------------------------------------------------------------------

$ = @joyJQ ? @$

class EventsCalendar
    constructor: () ->
        return

    enable: () ->
        @_enablePopup()
        $(window).resize () =>
            @_handleResize()
        @_handleResize()
        return

    _enablePopup: () ->
        if $("#joyous-overlay").length == 0
            $("""
  <div id="joyous-overlay" class="joy-overlay"></div>
  <div class="joy-popup joy-popup__outer">
    <div id="joyous-more-events" class="calendar joy-popup__content">
      <a class="joy-popup__close" href="#">×</a>
      <div class="joy-cal__day-title"></div>
      <div class="joy-days-events"></div>
    </div>
  </div>""").appendTo("body")
        $(".joy-overlay, .joy-popup__outer, .joy-popup__close").click () ->
            $(".joy-overlay, .joy-popup__outer").hide()
            return false
        $(".joy-popup__content").click (event) ->
            event.stopPropagation()

    _handleResize: () ->
        if $(".joy-cal--monthly").length > 0
            @_adjustDays()
        @_linkReadMore()
        return

    _adjustDays: () ->
        width = $(".joy-cal--monthly .joy-cal__day").first().outerWidth()
        height = $(".joy-cal--monthly .joy-cal__date").first().outerHeight()
        eventsHeight = (width - height) * 0.71
        $(".joy-cal--monthly .joy-days-events").outerHeight(eventsHeight)
        return

    _linkReadMore: () ->
        $(".joy-days-events").each (index, element) =>
            day = $(element).closest(".joy-cal__day")
            day.find(".joy-cal__read-more").remove()
            if (element.offsetHeight < element.scrollHeight or
                 element.offsetWidth < element.scrollWidth)
                @_addReadMoreLink(day)
            return
        return

    _addReadMoreLink: (day) ->
        link = $("<a>").attr('href', 'javascript:void 0')
                       .attr('title', "Show all of this day's events")
                       .addClass("joy-cal__read-more").text("+")
        link.click (ev) ->
            title = day.find(".joy-cal__day-title").clone()
            $("#joyous-more-events .joy-cal__day-title").replaceWith(title)
            events = day.find(".joy-days-events").clone().height('auto')
            $("#joyous-more-events .joy-days-events").replaceWith(events)
            y = Math.max(ev.pageY - 100, $(window).scrollTop())
            $(".joy-popup__outer").css('top', y)
            $("#joyous-overlay, .joy-popup__outer").show()
            return false
        day.append(link)
        return


$ ->
    calendar = new EventsCalendar()
    calendar.enable()
    return
