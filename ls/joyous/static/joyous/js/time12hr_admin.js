(function() {
  this.initTime12hrChooser = function(id) {
    $('#' + id).datetimepicker({
      datepicker: false,
      formatTime: 'g:ia',
      format: 'g:ia',
      step: 30
    });
  };

}).call(this);
