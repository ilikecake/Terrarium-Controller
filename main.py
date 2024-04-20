# Write your code here :-)
import time
import board
import digitalio
import pwmio
import time
import rtc
import json #TODO: Get rid of this eventually?
import supervisor #TODO: Get rid of this eventually?
import storage

#import circuitpython_schedule as schedule

from adafruit_datetime import time as time_obj
import terminalio
import displayio
from adafruit_display_text import label
import adafruit_ili9341
import adafruit_focaltouch
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

#from adafruit_bus_device import i2c_device
from adafruit_onewire.bus import OneWireBus
import adafruit_ds18x20
import neopixel
from adafruit_emc2101 import EMC2101
import adafruit_ds3231
import adafruit_sht4x

import i2c_expanders.PCAL9555 as PCAL9555
import i2c_expanders.PCAL9538 as PCAL9538

#import iot_device.iot_device as iot_device
#import iot_device.sensor as sensor
import iot_device.timer as timer

i2c_devices = [{"address": 0x20, "name": "PCAL9555 IO Expander"},
               {"address": 0x36, "name": "MAX17048 Battery Monitor"},
               {"address": 0x38, "name": "FT6202 Touch Controller"},
               {"address": 0x4C, "name": "EMC2101 Fan Controller"},
               {"address": 0x68, "name": "DS3231M Real Time Clock"},
               {"address": 0x70, "name": "PCAL9538 IO Expander"},       ]

timer_dev = timer.timer()

timer_dev.AddOutput("heatlamp")
timer_dev.AddOutput("uv")
timer_dev.AddOutput("led")

timer_dev.DisplayOutputs()


RelayList = []
timer_dev.AddEvent({"time":     time_obj(5, 30),
                    "led":      {"value": True},
                    "uv" :      {"value": True},
                    "heatlamp": {"value": True}})
timer_dev.AddEvent({"time": time_obj(20, 20), 
                    "led": {"value": True},
                    "uv":  {"value": False}})

timer_dev.AddEvent({"time": time_obj(19, 05), "heatlamp":{"value": False}})
timer_dev.AddEvent({"time": time_obj(9, 45),  "uv":{"value": True}})
timer_dev.AddEvent({"time": time_obj(11, 45), "heatlamp":{"value": True}})

timer_dev.ShowEventList() 

timer_dev.GenerateEventTable()

print("blarg")

time.sleep(300)






#wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
#pool = socketpool.SocketPool(wifi.radio)
#requests = adafruit_requests.Session(pool, ssl.create_default_context())
#print("IP:", wifi.radio.ipv4_address)

'''
import pwmio
import time
import rtc
import json #TODO: Get rid of this eventually?
import supervisor #TODO: Get rid of this eventually?
import storage

#import circuitpython_schedule as schedule

from adafruit_datetime import time as time_obj
import terminalio
import displayio
from adafruit_display_text import label
import adafruit_ili9341
import adafruit_focaltouch
try:
    from fourwire import FourWire
except ImportError:
    from displayio import FourWire

#from adafruit_bus_device import i2c_device
from adafruit_onewire.bus import OneWireBus
import adafruit_ds18x20
import neopixel
from adafruit_emc2101 import EMC2101
import adafruit_ds3231
import adafruit_sht4x

import i2c_expanders.PCAL9555 as PCAL9555
import i2c_expanders.PCAL9538 as PCAL9538

import iot_device.iot_device as iot_device
import iot_device.sensor as sensor
import iot_device.timer as timer
'''
i = 0

while True:
    i = i+1
    if i > 10:
        i = 0
    print(i)

    time.sleep(1)

'''
    print("GPIOs ON")
    print("HV: ", HV_Detect.value)
    LCD_Backlight.value = True
    GPIO_Pins[0].value = True
    GPIO_Pins[1].value = True
    GPIO_Pins[2].value = True
    GPIO_Pins[3].value = True
    Buzzer.value = True

    if ft.touched:
        print(ft.touches)
    else:
        print('no touch')


    time.sleep(5)
    IOT_dev.CaptureData()
    IOT_dev.SendSensorValues()
    print("GPIOs OFF")
    print("HV: ", HV_Detect.value)
    GPIO_Pins[0].value = False
    GPIO_Pins[1].value = False
    GPIO_Pins[2].value = False
    GPIO_Pins[3].value = False
    Buzzer.value = False
    LCD_Backlight.value = False

    if ft.touched:
        print(ft.touches)
    else:
        print('no touch')

    time.sleep(5)'''
