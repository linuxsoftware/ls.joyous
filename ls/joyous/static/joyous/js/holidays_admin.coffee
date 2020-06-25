#---------------------------------------------------------------------------
# Holidays form
#---------------------------------------------------------------------------
$ = @joyJQ ? @$ ? django.jQuery

allHolidaysChanged = () ->
    allHols = $("#id_all_holidays").prop("checked")
    #$(".multiple_choice_field").toggle(not allHols)
    if allHols
        $("li.multiple_choice_field").hide()
    else
        # Give the same height to the two boxes.
        $("li.multiple_choice_field").show()
        fromBox = $("#id_closed_for_from")
        fromFilter = $("#id_closed_for_filter")
        toBox = $("#id_closed_for_to")
        toBox.height(fromFilter.outerHeight() + fromBox.outerHeight())
    return

$ ->
    allHolidaysChanged()
    $("#id_all_holidays").click (ev) ->
        allHolidaysChanged()
        return true
    return
