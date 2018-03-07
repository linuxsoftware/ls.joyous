(function() {
  ({
    "version": 3,
    "names": [],
    "mappings": "",
    "sources": ["time12hr_admin.coffee"],
    "sourcesContent": ["#---------------------------------------------------------------------------\n# 12hr formatted time\n#---------------------------------------------------------------------------\n\n@initTime12hrChooser = (id) ->\n    $('#' + id).datetimepicker\n        datepicker: false\n        formatTime:'g:ia'\n        format: 'g:ia'\n        step: 30\n    return\n"],
    "file": "../time12hr_admin.coffee"
  });

}).call(this);
