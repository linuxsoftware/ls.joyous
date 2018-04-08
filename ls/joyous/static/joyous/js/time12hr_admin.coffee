#---------------------------------------------------------------------------
# 12hr formatted time
#---------------------------------------------------------------------------

time12hrFormat = "g:ia"

$ ->
    if $.datetimepicker?.setDateFormatter? and moment?
        time12hrFormat = "h:mma"
        $.datetimepicker.setDateFormatter("moment")
    return

@initTime12hrChooser = (id) ->
    $('#' + id).datetimepicker
        datepicker: false
        formatTime: time12hrFormat
        format: time12hrFormat
        step: 30
    return
