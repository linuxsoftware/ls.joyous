(function() {
  ({
    "version": 3,
    "names": [],
    "mappings": "",
    "sources": ["gulpfile.coffee"],
    "sourcesContent": ["process.env.NODE_DISABLE_COLORS=1\ngulp       = require \"gulp\"\nutil       = require \"gulp-util\"\nplumber    = require \"gulp-plumber\"\nnotify     = require \"gulp-notify\"\ncoffee     = require \"gulp-coffee\"\nsourcemaps = require \"gulp-sourcemaps\"\n\ngulp.task \"src.coffee\", ->\n  gulp.src  \"*.coffee\"\n      .pipe plumber notify.onError (err) ->\n          util.log(err)\n          title:   \"Burnt the coffee\"\n          message: \"" + err + "\"\n      .pipe coffee()\n      .pipe gulp.dest \".\"\n\ngulp.task \"src.coffee.with.maps\", ->\n  gulp.src  \"*.coffee\"\n      .pipe plumber notify.onError (err) ->\n          util.log(err)\n          title:   \"Burnt the coffee\"\n          message: \"" + err + "\"\n      .pipe sourcemaps.init()\n      .pipe sourcemaps.write(\"maps/\")\n      .pipe coffee()\n      .pipe gulp.dest \".\"\n\ngulp.task 'build', ['src.coffee.with.maps']\ngulp.task 'watch', ->\n  gulp.watch(\"*.coffee\", ['src.coffee.with.maps'])\n\ngulp.task('default', ['watch', 'build'])\n"],
    "file": "../gulpfile.coffee"
  });

}).call(this);
