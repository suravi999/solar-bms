#!/usr/bin/env python3
"""
based on https://github.com/sw-home/FHEM-BluetoothSmartBMS
"""

"""
test data:
generic:    data = b"\x053\xff\xb2I\xb8TS\x00\x01\'Y\x00\x00\x00\x00\x00\x00\x19W\x03\x04\x01\x0b\x06\xfbLw"
"""
import gatt
import json
import sys
import time

import sqlite3

from time import gmtime, strftime

manager = gatt.DeviceManager(adapter_name='hci0')

class AnyDevice(gatt.Device):
    def  __init__(self, **kwargs):
        super().__init__(**kwargs)

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))
        exit(1)

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))
    #    self.manager.stop()

    def services_resolved(self):
        super().services_resolved()

        device_information_service = next(
            s for s in self.services
            if s.uuid == '0000ff00-0000-1000-8000-00805f9b34fb')

        self.bms_read_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '0000ff01-0000-1000-8000-00805f9b34fb')

        self.bms_write_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '0000ff02-0000-1000-8000-00805f9b34fb')

        #print("BMS found")
        self.bms_read_characteristic.enable_notifications()

    def characteristic_enable_notifications_succeeded(self, characteristic):
        super().characteristic_enable_notifications_succeeded(characteristic)
        print("BMS notification succeeded:",repr(characteristic))
        #print("BMS request generic data")
        self.response=bytearray()
        self.rawdat={}
        self.get_voltages=False
        self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x03,0x00,0xFF,0xFD,0x77]));

    def characteristic_enable_notifications_failed(self, characteristic, error):
        super.characteristic_enable_notifications_failed(characteristic, error)
        print("BMS notification failed:",error)

    def characteristic_value_updated(self, characteristic, value):
        print(strftime("BMS update: %Y-%m-%d %H:%M:%S", gmtime()))
        print("lenvalue", repr(len(value)))
        print("BMS answering")
        self.response+=value
        if (self.response.endswith(b'w')):
            #print("BMS answer:", self.response.hex())
            self.response=self.response[4:]
            if len(value) == 15:
                pass
                                  #self.disconnect();
                #self.manager.stop()
                time.sleep(10)
                self.rawdat = {}
                self.get_voltages = False
            elif len(value) == 12: 
                self.rawdat['packV']=int.from_bytes(self.response[0:2], byteorder = 'big',signed=True)/100.0
                self.rawdat['Ibat']=int.from_bytes(self.response[2:4], byteorder = 'big',signed=True)/100.0
                self.rawdat['P']=round(self.rawdat['packV']*self.rawdat['Ibat'], 1)
                #self.rawdat['P']=round(self.rawdat['Vbat']*self.rawdat['Ibat'], 1)
                self.rawdat['Bal']=int.from_bytes(self.response[12:14],byteorder = 'big',signed=False)
                self.rawdat['Ah_remaining']=int.from_bytes(self.response[4:6], byteorder='big', signed=True)/100
                self.rawdat['Ah_full']=int.from_bytes(self.response[6:8], byteorder='big', signed=True)/100
                self.rawdat['Ah_percent']=round(self.rawdat['Ah_remaining'] / self.rawdat['Ah_full'] * 100, 2)
                self.rawdat['Cycles']=int.from_bytes(self.response[8:10], byteorder='big', signed=True)

                for i in range(int.from_bytes(self.response[22:23],'big')): # read temperatures
                    self.rawdat['T{0:0=1}'.format(i+1)]=(int.from_bytes(self.response[23+i*2:i*2+25],'big')-2731)/10

                #print("BMS request voltages")
                #self.get_voltages=True
                self.response=bytearray()
                #self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x04,0x00,0xFF,0xFC,0x77]));
                print("Capacity: {capacity}% ({Ah_remaining} of {Ah_full}Ah)\nPower: {power}W ({I}Ah)\nTemperature: {temp}°C\nCycles: {cycles}\n".format(
                    capacity=self.rawdat['Ah_percent'],
                    Ah_remaining=self.rawdat['Ah_remaining'],
                    Ah_full=self.rawdat['Ah_full'],
                    power=self.rawdat['P'],
                    I=self.rawdat['Ibat'],
                    temp=self.rawdat['T1'],
                    cycles=self.rawdat['Cycles'],
                    ))
                print(repr(self.rawdat))               

                time.sleep(10)
                # Resend query
                self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x03,0x00,0xFF,0xFD,0x77]));

    def characteristic_write_value_failed(self, characteristic, error):
        print("BMS write failed:",error)
        exit(1)

def main():
    if (len(sys.argv)<2):
        print("Usage: bmsinfo.py <device_uuid>")
    else:
        #while True:
        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
        device = AnyDevice(mac_address=sys.argv[1], manager=manager)
        device.connect()
        #func_timeout.func_timeout(5, device.connect())
        #import ipdb; ipdb.set_trace()
        manager.run()
        print("sleep 10 sec")
        time.sleep(10)

if __name__ == "__main__":
  main()