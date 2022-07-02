const util = require('util'),
    EventEmitter = require('events').EventEmitter

var BluetoothBMS = function (deviceSettings, evEmitter, noble) {
    var _self = this;

    // config
    const deviceId = deviceSettings.deviceId; //device id on network

    let msgQueue = [],
        allBuffer = new Buffer(0), //temporary buffer collection
        writeNode = undefined,
        readNode = undefined;

    function onSerialData(data) {
        updateBuffer(data);
        //evEmitter.emit('bmsdata', data); //original bus message
    }

    function queueMessageHex(hexMessageWithSpaces) {
        const chars = hexMessageWithSpaces.split(' ');
        let msg = [];
        for (let i = 0; i < chars.length; i++) {
            msg.push('0x' + chars[i]);
        }
        const msgBuff = new Buffer(msg);
        queueMessage(msgBuff);
    }

    function queueMessage(bufferMessage) {
        if (bufferMessage.length > 0) {
            msgQueue.push({
                content: bufferMessage,
                status: 0
            }); //add message to queue with default status
        }
        if (msgQueue.length > 0) {
            writeMessageToSerial(msgQueue[0]);
        }
    }

    function writeMessageToSerial() {
        let msg = msgQueue[0];
        if (msg !== undefined && msg.status === 0) {
            if (writeNode !== undefined) {
                writeNode.write(new Buffer(msg.content), false, function (error) {
                    if (error) {
                        console.log("write failed: " + JSON.stringify(error));
                    }
                });
            } else {
                console.log("write failed: no destination");
            }
            //console.log('write: ' + JSON.stringify(msg));
            msg.status = 1; //sending message
            _self.emit('sent', msg.content);
        }
    }

    function updateBuffer(dataBuff) {
        //Collect buffer and compose message
        if (allBuffer.length > 0) {
            allBuffer = Buffer.concat([allBuffer, dataBuff]);
        } else {
            allBuffer = new Buffer(dataBuff);
        }

        if (allBuffer.length > 4) {
            if (allBuffer[0] === 221 && dataBuff[dataBuff.length - 1] === 119) { //DD A5 (5A) LL LL ... 77
                const mlen = (allBuffer[2] * (16 * 16)) + (allBuffer[3]);
                if (mlen > 0 && allBuffer.length >= mlen + 7) {
                    const buffMsg = new Buffer(msgQueue[0].content); //get message copy
                    msgQueue.shift();
                    _self.emit('data', {
                        command: buffMsg,
                        response: new Buffer(allBuffer)
                    });
                    allBuffer = new Buffer(0);
                }
            }
        }

        if (dataBuff[dataBuff.length - 1] === 119 && allBuffer.length > 0 && (allBuffer[0] !== 221 && allBuffer[1] !== 165)) { //77
            _self.emit('data', {
                command: null,
                response: allBuffer
            });
            allBuffer = new Buffer(0);
        }

        if (allBuffer.length === 0) {
            //update queue
            if (msgQueue.length > 0 && msgQueue[0].status === 1) {
                msgQueue.shift();
            }
            if (msgQueue.length > 0) {
                writeMessageToSerial();
            }
        }
    }

    _self.sendMessage = function (bufferMsg) {
        queueMessage(bufferMsg);
    }

    _self.isReady = function () {
        return msgQueue.length === 0;
    }

    _self.setWriteNode = function (writenode) {
        writeNode = writenode;
    }
    _self.setReadNode = function (readnode) {
        readNode = readnode;
        readNode.on('read', function (data, notification) {
            if (notification) { // if you got a notification
                onSerialData(data);
            } else {
                //console.log(device.settings.deviceId, 'data: ' + data.toString());
            }
        });
    }
};

util.inherits(BluetoothBMS, EventEmitter);
module.exports = BluetoothBMS;