const express = require('express'),
  fs = require('fs'),
  path = require('path'),
  favicon = require('serve-favicon'),
  index = require('./routes/index');
let settings = require('./bin/settings');

//config settings - load settings from file
settings = settings.load();

let app = express();

// Event emitter
const EventEmitter = require('events');
class CarCtrlEmitter extends EventEmitter { }
const evEmitter = new CarCtrlEmitter();
console.log('EventEmitter created.');

// BMS dependencies and settings.
const Bms = require('./bin/bmsdevice.js');
const bms = new Bms(settings, evEmitter);

// view engine setup - HTML
app.use(express.static(__dirname + '/public'));
app.set('views', path.join(__dirname, 'views'));

// uncomment after placing your favicon in /public
app.use(favicon(path.join(__dirname, 'public', 'favicon.ico')));
app.use(express.static(path.join(__dirname, 'public')));

app.use('/', index);

// catch 404 and forward to error handler
app.use(function (req, res, next) {
  let err = new Error('Not Found');
  err.status = 404;
  next(err);
});

// error handler
app.use(function (err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error');
});

exports.app = app;
exports.evEmitter = evEmitter;
exports.bms = bms;