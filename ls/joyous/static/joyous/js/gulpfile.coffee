process.env.NODE_DISABLE_COLORS=1
gulp       = require "gulp"
util       = require "gulp-util"
plumber    = require "gulp-plumber"
notify     = require "gulp-notify"
crashsound = require "gulp-crash-sound"
coffee     = require "gulp-coffee"
sourcemaps = require "gulp-sourcemaps"

gulp.task "src.coffee", ->
  gulp.src  "*.coffee"
      .pipe plumber crashsound.plumb notify.onError (err) ->
          util.log(err)
          title:   "Burnt the coffee"
          message: "#{err}"
      .pipe coffee()
      .pipe gulp.dest "."

gulp.task "src.coffee.with.maps", ->
  gulp.src  "*.coffee"
      .pipe plumber crashsound.plumb notify.onError (err) ->
          util.log(err)
          title:   "Burnt the coffee"
          message: "#{err}"
      .pipe sourcemaps.init()
      .pipe sourcemaps.write("maps/")
      .pipe coffee()
      .pipe gulp.dest "."

gulp.task 'build', ['src.coffee.with.maps']
gulp.task 'watch', ->
  gulp.watch("*.coffee", ['src.coffee.with.maps'])

gulp.task('default', ['watch', 'build'])
