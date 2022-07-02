//module settings.js
const fs = require('fs'),
    filename = ('settings.json');

settings = {
    devices:
        [],
    monitor: {
        refreshInterval: 1000, //ms
        autoStart: false,
        logToFile: false
    },
    load: function () {
        return JSON.parse(fs.readFileSync(filename));
    },
    save: function () {
        fs.writeFileSync(filename, JSON.stringify(this));
    }
};

module.exports = settings;