#---------------------------------------------------------------------------
# Holidays form
#---------------------------------------------------------------------------
$ = @joyJQ ? @$ ? django.jQuery

allHolidaysChanged = () ->
    allHols = $("#id_all_holidays").prop("checked")
    $(".multiple_choice_field").toggle(not allHols)
    return

$ ->
    allHolidaysChanged()
    $("#id_all_holidays").click (ev) ->
        allHolidaysChanged()
        return true
    return
