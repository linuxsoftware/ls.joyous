#---------------------------------------------------------------------------
# 12hr formatted time
#---------------------------------------------------------------------------

time12hrFormat = "g:ia"

$ ->
    if $.datetimepicker?.setDateFormatter? and moment?
        time12hrFormat = "moment+12hr"
        phpDateFormatter = new DateFormatter()
        $.datetimepicker.setDateFormatter
            parseDate: (date, format) ->
                if format == "moment+12hr"
                    mo = moment(date, ["h:mma",
                                       "ha",
                                       "h:m:sa",
                                       "HH:mm",
                                       "HH:mm:s",
                                       "h"])
                    if mo.isValid()
                        return mo.toDate()
                    else
                        return false
                else
                    return phpDateFormatter.parseDate(date, format)

            formatDate: (date, format) ->
                if format == "moment+12hr"
                    return moment(date).format("h:mma")
                else
                    return phpDateFormatter.formatDate(date, format)
        return

@initTime12hrChooser = (id) ->
    $('#' + id).datetimepicker
        datepicker: false
        formatTime: time12hrFormat
        format: time12hrFormat
        step: 30
    return
