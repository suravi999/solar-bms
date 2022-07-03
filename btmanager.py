import gatt
import json

import datetime
import sys
import time
import InfluxdataManager

global data
#data = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
data = {}

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

        print("BMS found")
        self.bms_read_characteristic.enable_notifications()

    def characteristic_enable_notifications_succeeded(self, characteristic):
        super().characteristic_enable_notifications_succeeded(characteristic)
        print("BMS request generic data")
        self.response=bytearray()
        self.rawdat={}
        self.get_voltages=False
        self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x03,0x00,0xFF,0xFD,0x77]));

    def characteristic_enable_notifications_failed(self, characteristic, error):
        super.characteristic_enable_notifications_failed(characteristic, error)
        print("BMS notification failed:",error)

    def characteristic_value_updated(self, characteristic, value):
        print("BMS answering")
        self.response+=value
        print("BMS answering", self.response)
        if (self.response.endswith(b'w')):
            print("BMS answer:", self.response.hex())
            self.response=self.response[4:]
            if (self.get_voltages):
                packVolts=0
                for i in range(int(len(self.response)/2)-1):
                    cell=int.from_bytes(self.response[i*2:i*2+2], byteorder = 'big')/1000
                    self.rawdat['V{0:0=2}'.format(i+1)]=cell
                    packVolts+=cell
                # + self.rawdat['V{0:0=2}'.format(i)]
                self.rawdat['Vbat']=packVolts
                self.rawdat['P']=round(self.rawdat['Vbat']*self.rawdat['Ibat'], 1)

                data['Ah_percent'] = self.rawdat['Ah_percent']
                data['Ah_remaining'] = self.rawdat['Ah_remaining']
                data['Ah_full'] = self.rawdat['Ah_full']
                data['P'] = self.rawdat['P']
                data['Vbat'] = self.rawdat['Vbat']
                data['Ibat'] = self.rawdat['Ibat']
                data['T1'] = self.rawdat['T1']
                data['Cycles'] = self.rawdat['Cycles']
                data['T2'] = self.rawdat['T2']
                data['V01'] = self.rawdat['V01']
                data['V02'] = self.rawdat['V02']
                data['V03'] = self.rawdat['V03']
                data['V04'] = self.rawdat['V04']
                data['V05'] = self.rawdat['V05']
                data['V06'] = self.rawdat['V06']
                data['V07'] = self.rawdat['V07']
                data['V08'] = self.rawdat['V08']
                data['V09'] = self.rawdat['V09']
                data['V10'] = self.rawdat['V10']
                data['V11'] = self.rawdat['V11']
                data['V12'] = self.rawdat['V12']
                data['V13'] = self.rawdat['V13']
                data['V14'] = self.rawdat['V14']
                data['V15'] = self.rawdat['V15']
                data['V16'] = self.rawdat['V16']
                data['Bal'] = self.rawdat['Bal']
                data['State'] = self.rawdat['State']
                data['FET_St'] = self.rawdat['FET_St']

                InfluxdataManager.SendData(data)
                print(data)

                self.manager.stop()
            else:
                self.rawdat['packV']=int.from_bytes(self.response[0:2], byteorder = 'big',signed=True)/100.0
                self.rawdat['Ibat']=int.from_bytes(self.response[2:4], byteorder = 'big',signed=True)/100.0
                self.rawdat['Ah_remaining']=int.from_bytes(self.response[4:6], byteorder='big', signed=True)/100
                self.rawdat['Ah_full']=int.from_bytes(self.response[6:8], byteorder='big', signed=True)/100
                self.rawdat['Cycles']=int.from_bytes(self.response[8:10], byteorder='big', signed=True)
                self.rawdat['Bal']=int.from_bytes(self.response[12:14],byteorder = 'big',signed=False)
                self.rawdat['State']=int.from_bytes(self.response[16:18], byteorder = 'big',signed=False)
                self.rawdat['FET_St']=int.from_bytes(self.response[20:21], byteorder = 'big',signed=False)
                self.rawdat['Ah_percent']=round(self.rawdat['Ah_remaining'] / self.rawdat['Ah_full'] * 100, 2)

                for i in range(int.from_bytes(self.response[22:23],'big')): # read temperatures
                    self.rawdat['T{0:0=1}'.format(i+1)]=(int.from_bytes(self.response[23+i*2:i*2+25],'big')-2731)/10

                print("BMS request voltages")
                self.get_voltages=True
                self.response=bytearray()
                self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x04,0x00,0xFF,0xFC,0x77]));

    def characteristic_write_value_failed(self, characteristic, error):
        print("BMS write failed:",error)



if (len(sys.argv)<2):
    print("Usage: bms-shed.py <device_uuid>")
else:
    while True:
        try:
            device = AnyDevice(mac_address=sys.argv[1], manager=manager)
            print("main AnyDevice")
            device.connect()
            print("main device.connect")
            manager.run()
        except:
            pass
        time.sleep(60)