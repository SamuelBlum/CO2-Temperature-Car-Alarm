#/usr/bin/env python

# @author astaff
#
# This sample is to demonstrate DeviceHive Python library
# Connect LED to PIN11 of the board and 1-wire sensor to GPIO4 board PIN #7,
# use pins #1 (3v3) or #2 (5v) for power and pin #6 for ground
#
# (C) DataArt Apps, 2012
# Distributed under MIT license
#

import sys
import os
import time
from time import sleep

try :
    import RPi.GPIO as GPIO
except ImportError:
    class FakeGPIO(object):
        OUT = 'OUTPUT BCM.GPIO17'
        BOARD = 'BOARD'
        def __init__(self):
            print 'Fake gpio initialized'
        def setmode(self, value):
            print 'Set mode {0}.'.format(value)
        def setup(self, io, mode):
            print 'Set gpio {0}; Mode: {1};'.format(io, mode)
        def output(self, io, vlaue):
            print 'Set gpio {0}; Value: {1};'.format(io, vlaue)
    GPIO = FakeGPIO()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from zope.interface import implements
from twisted.python import log
from twisted.internet import reactor, task

import devicehive
import devicehive.auto


# change it to match your address for 1-wire sensor
_W1_FILENAME='/sys/bus/w1/devices/28-000004fd9c29/w1_slave'
if not os.path.exists(_W1_FILENAME) :
    _W1_FILENAME = '/dev/null'

# Board's pin #11 (GPIO17)
_LED_PIN=11

# API URL (register for free playground at http://beta2.devicehive.com/playground
_API_URL = 'http://nn1668.pg.devicehive.com/api/'

#
# for easier reading, this class holds all registration information for DeviceHive
#
class RasPiConfig(object):
    
    implements(devicehive.interfaces.IDeviceInfo)
    
    @property
    def id(self):
        return '9f33566e-1f8f-11e2-8979-c42c030dd6a5'
    
    @property
    def key(self):
        return 'device-key'
    
    @property
    def name(self):
        return 'Device1'
    
    @property
    def status(self):
        return 'Online'
    
    @property
    def network(self):
        return devicehive.Network(key = 'Netname', name = 'Netname', descr = 'RasPi/Py LED/w1 sample')
    
    @property
    def device_class(self):
        return devicehive.DeviceClass(name = 'Class1', version = '1.0', is_permanent = False)
    
    @property
    def equipment(self):
        return [devicehive.Equipment(name = 'LED', code = 'LED', type = 'Controllable LED'), devicehive.Equipment(name = 'THERMO', code = 'CO2', type = 'CO2Sensor')]

#
# This class handles DeviceHive API calls for our device
#
class RasPiApp(object):
    
    implements(devicehive.interfaces.IProtoHandler)
    
    def __init__(self, led, sensor):
        super(RasPiApp, self).__init__()
        self.connected = False
        self.notifs = []
        self.info = RasPiConfig()
        self.led = led
        self.sensor = sensor
    
    def on_apimeta(self, websocket_server, server_time):
        log.msg('on_apimeta')
    
    def on_connected(self):
        lc = task.LoopingCall(self.sensor.get_CO2, self)
        lc.start(1)
        
        log.msg('Connected to devicehive server.')
        self.connected = True
        for onotif in self.notifs :
            self.factory.notify(onotif['notification'], onotif['parameters'], device_id = self.info.id, device_key = self.info.key)
        self.notifs = []
        def on_subscribe(result) :
            self.factory.subscribe(self.info.id, self.info.key)
        def on_failed(reason) :
            log.err('Failed to save device {0}. Reason: {1}.'.format(self.info, reason))
        self.factory.device_save(self.info).addCallbacks(on_subscribe, on_failed)
    
    def on_connection_failed(self, reason) :
        pass
    
    def on_closing_connection(self):
        pass
    
    def on_failure(self, device_id, reason):
        pass
    
    def do_short_command(self, finished, equipment = None, state = 0):
        log.msg('Setting {0} equipment to {1}'.format(equipment, state))
        if equipment == 'LED' :
            if int(state) == 0 :
                self.led.set_off()
            else:
                self.led.set_on()
        # upon completion post the result back
        self.factory.notify('equipment', {'state': state, 'equipment': 'LED'}, device_id = self.info.id, device_key = self.info.key)
        finished.callback(devicehive.CommandResult('Completed'))
    
    def on_command(self, device_id, command, finished):
        # Expecting command as 'UpdateState' and parameters as {"equipment" : "LED", "state" : "0"}
        if command.command == 'UpdateLedState' :
            self.do_short_command(finished,  **command.parameters)
        else :
            finished.errback()
        # end do_command
    
    def notify(self, notif, **params):
        if self.connected :
	    print "beginnin test"
            print notif
	    print params
	    print "end test"
            self.factory.notify(notif, params, device_id = self.info.id, device_key = self.info.key)
        else :
            self.notifs.append({'notification': notif, 'parameters': params})


#
# CO2 sensor wrapper. Gets CO2 readings form file, parses them
# and notifies the services is the difference is greater than a certain threshold
#
class CO2Sensor(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self.last_CO2 = 0
        self.last_good_CO2 = 0
    
    # internal, get CO2 readings from device and check CRC
    def _get_CO2(self):
        with open(self.file_name) as f:
            content = f.readlines()
            for line in content:
                # sometimes CRC is bad, so we will return last known good CO2
                if line.find('crc=')>=0 and line.find('NO')>=0:
                    return self.last_good_CO2
                p = line.find('t=')
                if p >= 0:
                    self.last_good_CO2 = float(line[p+2:])/1000.0
                    return self.last_good_CO2
        return 0.0

    # check CO2, if greater than threshold, notify
    def get_CO2(self, dev):
        CO2 = self._get_CO2()
        if abs(CO2 - self.last_CO2) > 0.2:
            log.msg('CO2 {0} -> {1}'.format(self.last_CO2, CO2))
            dev.notify('equipment', CO2 = CO2, equipment = "CO2")
            self.last_CO2 = CO2

#
# Wrapper from LED connected to RasPi
#
class LedDevice(object):
    def __init__(self, pin):
        # We are using board PIN numbering (as opposed to chip's numbers)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin, GPIO.OUT)

    def blink(self, count):
        for i in range(count):
            GPIO.output(_LED_PIN,True)
            sleep(0.2)
            GPIO.output(_LED_PIN,False)
            sleep(0.2)

    def set_on(self):
        GPIO.output(_LED_PIN, True)

    def set_off(self):
        GPIO.output(_LED_PIN, False)

#
# main
#
if __name__ == '__main__' :
    log.startLogging(sys.stdout)
    
    led = LedDevice(_LED_PIN)
    # Blink on start to ensure device is working
    led.blink(3)

    # create CO2 sensor and queue it to check for CO2 in a separate thread
    CO2Sensor = CO2Sensor(_W1_FILENAME)
    
    # create a delegate to handle commands
    device = RasPiApp(led, CO2Sensor)
    led_factory = devicehive.auto.AutoFactory(device)
    led_factory.connect(_API_URL)   
    
    # off we go!
    reactor.run()

