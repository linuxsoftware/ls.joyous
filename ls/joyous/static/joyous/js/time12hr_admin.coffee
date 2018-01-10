#---------------------------------------------------------------------------
# 12hr formatted time
#---------------------------------------------------------------------------

@initTime12hrChooser = (id) ->
    $('#' + id).datetimepicker
        datepicker: false
        formatTime:'g:ia'
        format: 'g:ia'
        step: 30
    return
