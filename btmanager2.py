import gatt
import json

import datetime
import sys
import time

import click

from time import gmtime, strftime

from prometheus_client import Gauge, start_http_server, Enum

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
                data['Bal'] = self.rawdat['Bal']
                data['State'] = self.rawdat['State']
                data['FET_St'] = self.rawdat['FET_St']

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



class Metrics():

    def __init__(self):
        self.last_update_gauge = Gauge('bms_last_update', 'Metrics of last update')
        self.ah_percent_gauge = Gauge('bms_ah_percent', 'Metrics of percent of capacity')
        self.ah_remaining_gauge = Gauge('bms_ah_remaining', 'Metrics of remaining capcity')
        self.ah_full_gauge = Gauge('bms_ah_full', 'Metrics of full capacity')
        self.power_gauge = Gauge('bms_power', 'Metrics of power')
        self.voltage_gauge = Gauge('bms_voltage', 'Metrics of voltage')
        self.current_gauge = Gauge('bms_current', 'Metrics of current')
        self.temperature_gauge = Gauge('bms_temperature', 'Metrics of temperature')
        self.cycles_gauge = Gauge('bms_cycles', 'Metrics of cycles')
        self.mode_enum = Enum('bms_mode', 'Metrics of mode', states=['discharging', 'charging'])
        self.time_left = Gauge('bms_time_left', 'Metrics of time to charge/discharge', ['mode'])
        self.temperature2_gauge = Gauge('bms_temperature2', 'Metrics of temperature2')
        self.voltage01_gauge = Gauge('bms_voltage01', 'Metrics of voltage01')
        self.voltage02_gauge = Gauge('bms_voltage02', 'Metrics of voltage02')
        self.voltage03_gauge = Gauge('bms_voltage03', 'Metrics of voltage03')
        self.voltage04_gauge = Gauge('bms_voltage04', 'Metrics of voltage04')
        self.voltage05_gauge = Gauge('bms_voltage05', 'Metrics of voltage05')
        self.voltage06_gauge = Gauge('bms_voltage06', 'Metrics of voltage06')
        self.voltage07_gauge = Gauge('bms_voltage07', 'Metrics of voltage07')
        self.voltage08_gauge = Gauge('bms_voltage08', 'Metrics of voltage08')
        #self.bal_gauge = Gauge('bms_bal', 'Metrics of bal')
        self.bal_status = Gauge('bms_balance_status', 'Metrics of balance status', ['cell'])
        self.bms_state = Gauge('bms_state', 'Metrics of bms state', ['state'])
        self.bms_fetst = Gauge('bms_fetst', 'Metrics of bms fetst', ['fetst'])

    def build_metrics(self):
        last_update = datetime.datetime.now()
        # last_update = datetime.datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
        last_update = last_update.timestamp()
        self.last_update_gauge.set(last_update)
        self.ah_percent_gauge.set(data['Ah_percent'])
        ah_remaining_gauge = data['Ah_remaining']
        self.ah_remaining_gauge.set(ah_remaining_gauge)
        ah_full_gauge = data['Ah_full']
        self.ah_full_gauge.set(ah_full_gauge)
        self.power_gauge.set(data['P'])
        self.voltage_gauge.set(data['Vbat'])
        self.current_gauge.set(data['Ibat'])
        self.temperature_gauge.set(data['T1'])
        self.cycles_gauge.set(data['Cycles'])
        self.temperature2_gauge.set(data['T2'])
        self.voltage01_gauge.set(data['V01'])
        self.voltage02_gauge.set(data['V02'])
        self.voltage03_gauge.set(data['V03'])
        self.voltage04_gauge.set(data['V04'])
        self.voltage05_gauge.set(data['V05'])
        self.voltage06_gauge.set(data['V06'])
        self.voltage07_gauge.set(data['V07'])
        self.voltage08_gauge.set(data['V08'])

        celbals = [0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0]
        for num in range(0,8):
            celbals[num] = ( data['Bal']>>num ) & 0b1
        self.bal_status.labels(cell='celbals[1]').set(celbals[0])
        self.bal_status.labels(cell='celbals[2]').set(celbals[1])
        self.bal_status.labels(cell='celbals[3]').set(celbals[2])
        self.bal_status.labels(cell='celbals[4]').set(celbals[3])
        self.bal_status.labels(cell='celbals[5]').set(celbals[4])
        self.bal_status.labels(cell='celbals[6]').set(celbals[5])
        self.bal_status.labels(cell='celbals[7]').set(celbals[6])
        self.bal_status.labels(cell='celbals[8]').set(celbals[7])

        bms_state = [0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0,0b0]
        for num in range(0,13):
            bms_state[num] = ( data['State']>>num ) & 0b1
        self.bms_state.labels(state='Cell_Block_Over_Vol').set(bms_state[0])
        self.bms_state.labels(state='Cell_Block_Under_Vol').set(bms_state[1])
        self.bms_state.labels(state='Battery_Over_Vol').set(bms_state[2])
        self.bms_state.labels(state='Battery_Under_Vol').set(bms_state[3])
        self.bms_state.labels(state='Charging_Over_Temp').set(bms_state[4])
        self.bms_state.labels(state='Charging_Under_Temp').set(bms_state[5])
        self.bms_state.labels(state='Discharging_Over_Temp').set(bms_state[6])
        self.bms_state.labels(state='Discharging_Under_Temp').set(bms_state[7])
        self.bms_state.labels(state='Charging_Over_Current').set(bms_state[8])
        self.bms_state.labels(state='Discharging_Over_Current').set(bms_state[9])
        self.bms_state.labels(state='Short_Circuit').set(bms_state[10])
        self.bms_state.labels(state='Fore-end_IC_Error').set(bms_state[11])
        self.bms_state.labels(state='MOS_Software_Lock-in').set(bms_state[12])

        fet_state = [0b0,0b0]
        for num in range(0,2):
            fet_state[num] = ( data['FET_St']>>num ) & 0b1
        self.bms_fetst.labels(fetst='FET_charging').set(fet_state[0])
        self.bms_fetst.labels(fetst='FET_discharging').set(fet_state[1])

        if float(data['P']) >= 0:
            mode = 'charging'
        else:
            mode = 'discharging'

        self.mode_enum.state(mode)


if (len(sys.argv)<2):
    print("Usage: bms-shed.py <device_uuid>")
else:
    start_http_server(8000)
    metrics = Metrics()
    while True:
        device = AnyDevice(mac_address=sys.argv[1], manager=manager)
        print("main AnyDevice")
        device.connect()
        print("main device.connect")
        manager.run()
        print("main manager.run")
        metrics.build_metrics()
        print("main metrics.build_metrics")
        time.sleep(10)