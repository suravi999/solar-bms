import gatt
import json
import sys

from time import gmtime, strftime

manager = gatt.DeviceManager(adapter_name='hci0')

class AnyDevice(gatt.Device):
    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))
        self.manager.stop()

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
        self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x04,0x00,0xFF,0xFD,0x77]));

    def characteristic_enable_notifications_failed(self, characteristic, error):
        super.characteristic_enable_notifications_failed(characteristic, error)
        print("BMS notification failed:",error)

    def characteristic_value_updated(self, characteristic, value):
        print("characteristic_value_updated",value)
        print(strftime("BMS update: %Y-%m-%d %H:%M:%S", gmtime()))
        print("lenvalue", repr(len(value)))
        print("BMS answering")
        self.response+=value
        if (self.response.endswith(b'w')):
            print("BMS answer:", self.response.hex())
            try:
                self.rawdat['AA']=int.from_bytes(self.response[0:2], byteorder = 'big',signed=True)
                self.rawdat['BB']=int.from_bytes(self.response[2:4], byteorder = 'big',signed=True)
            except Exception as e:
                print(e)
            self.response=self.response[4:]
            if (self.get_voltages):
                packVolts=0
                for i in range(int(len(self.response)/2)-1):
                    cell=int.from_bytes(self.response[i*2:i*2+2], byteorder = 'big')/1000
                    self.rawdat['V{0:0=2}'.format(i+1)]=cell
                    packVolts+=cell
# + self.rawdat['V{0:0=2}'.format(i)]
                self.rawdat['Vbat']=packVolts
                #self.rawdat['Ah_remaining1']= (int.from_bytes(self.response[8:9], byteorder='big', signed=True) * 16 * 16 + int.from_bytes(self.response[9], byteorder='big', signed=True)) * 10      #int.from_bytes(self.response[4:6], byteorder='big', signed=True)/100
                
                print("BMS chat ended")
                print (json.dumps(self.rawdat, indent=1, sort_keys=True))
                #self.get_voltages=False
                self.disconnect();
            else:

                #self.rawdat['Ah_remaining1']= (self.response[8] * 16 * 16 + self.response[9]) * 10
                self.rawdat['Ah_remaining']= (int.from_bytes(self.response[3:4], byteorder='big', signed=True))     #int.from_bytes(self.response[4:6], byteorder='big', signed=True)/100
                self.rawdat['Ah_full']=int.from_bytes(self.response[6:8], byteorder='big', signed=True)/100
                self.rawdat['Cycles']=int.from_bytes(self.response[8:10], byteorder='big', signed=True)


                self.rawdat['Ibat']=int.from_bytes(self.response[2:4], byteorder = 'big',signed=True)/100.0
                print("bal byte value",self.response[12:14])
                self.rawdat['Bal']=int.from_bytes(self.response[12:14],byteorder = 'big',signed=False)
                for i in range(int.from_bytes(self.response[22:23],'big')): # read temperatures
                    self.rawdat['T{0:0=1}'.format(i+1)]=(int.from_bytes(self.response[23+i*2:i*2+25],'big')-2731)/10

                print("BMS request voltages")
                self.get_voltages=True
                self.response=bytearray()
                self.bms_write_characteristic.write_value(bytes([0xDD,0xA5,0x03,0x00,0xFF,0xFD,0x77]));

    def characteristic_write_value_failed(self, characteristic, error):
        print("BMS write failed:",error)


if (len(sys.argv)<2):
    print("Usage: bmsinfo.py <device_uuid>")
else:
    ma = 'A4:C1:37:50:2C:2B'
    device = AnyDevice(mac_address=sys.argv[1], manager=manager)
    device.connect()
    manager.run()