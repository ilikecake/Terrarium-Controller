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
import gc

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

i2c_devices = [{"address": 0x20, "name": "PCAL9555 IO Expander"},
               {"address": 0x36, "name": "MAX17048 Battery Monitor"},
               {"address": 0x38, "name": "FT6202 Touch Controller"},
               {"address": 0x4C, "name": "EMC2101 Fan Controller"},
               {"address": 0x68, "name": "DS3231M Real Time Clock"},
               {"address": 0x70, "name": "PCAL9538 IO Expander"},       ]
               
IOT_dev = iot_device.iot_device()
timer_dev = timer.timer()

timer_dev.AddOutput("heatlamp")
timer_dev.AddOutput("uv")
timer_dev.AddOutput("led")
timer_dev.AddOutput("tstat")
#timer_dev.DisplayOutputs()

blart = time.struct_time((0,0,0,13,44,0,0,0,0))


#timer_dev.GenerateEventTable()

RelayList = []
timer_dev.AddEvent({"time":     time_obj(5, 30),
                    "led":      {"value": True},
                    "uv" :      {"value": True}})
timer_dev.AddEvent({"time": time_obj(20, 20), 
                    "led": {"value": False},
                    "uv":  {"value": False}})

timer_dev.AddEvent({"time": blart, "heatlamp":{"value": False}})
timer_dev.AddEvent({"time": time_obj(19, 05), "heatlamp":{"value": False}})
timer_dev.AddEvent({"time": time_obj(9, 45),  "uv":{"value": True}})
timer_dev.AddEvent({"time": time_obj(11, 45), "heatlamp":{"value": True}})

timer_dev.AddEvent({"time": time_obj(9, 45),  "heatlamp":{"value": True},  "led":{"value": False}})
timer_dev.RemoveEvent({"time": time_obj(9, 45),  "heatlamp":{"value": True},  "uv":{"value": True}})

timer_dev.AddEvent({"time": time_obj(9, 15), "tstat":{"value": 82}})
timer_dev.AddEvent({"time": time_obj(18, 45), "tstat":{"value": 72}})

#timer_dev.ShowEventList(ShowRaw = True)
timer_dev.ShowEventList()
timer_dev.ShowEventList(ShowCalc = True)

#TODO: put generate event table function at the end of the add event function

#print("11:44:", timer_dev.GetCurrentState(time_obj(11, 44)))
#print("11:45:", timer_dev.GetCurrentState(time_obj(11, 45)))
#print("11:46:", timer_dev.GetCurrentState(time_obj(11, 46)))
#print("21:00:", timer_dev.GetCurrentState(time_obj(21, 0)))

#print('blarg')
time.sleep(3)
#---------------------------------------------------------------------------------------------------
#I2C Devices
# *0x20 - PCAL9555 IO Expander
# *0x36 - MAX17048 Battery Monitor (onboard) TODO: this might be a LC709203 at address 0x0B instead. Check this sometime.
# *0x38 - FT6202 Touch Controller
# *0x4C - EMC2101 Fan Controller
# *0x68 - DS3231M RTC
# *0x70 - PCAL9538 IO Expander

#TODO: It seems like the first read to the DS18b20 device fails with a CRC error.
#  This catches the error. Maybe instead do a few dummy reads right after initialization of the device?
#def DS18x20_GetTemp(dev):
#    try:
#        temp = dev.temperature 
#    except RuntimeError:
#        print("CRC Error getting temp")
#        temp = 0
#   return temp

#Returns temp in dec C
def sht_temp_getdata(busdev, busID):
    return (busdev.temperature*(9/5)+32)

def sht_humid_getdata(busdev, busID):
    return busdev.relative_humidity

def i2c_unstick(i2c_bus):
    while not i2c.try_lock():
        pass

    for i in range(8):
        try:
            i2c.writeto(0x00, b"1")
        except OSError as err:
            #Known errors:
            # [Errno 19] No such device : Normal error if we try to write to a non-existant device.
            # [Errno 116] ETIMEDOUT     : This error seems to occur when the bus is stuck. I have seen it when the clock line is stuck low. It appears that this takes ~1.2 sec to timeout.
            if err.args[0] == 19:
                #This error indicates the bus is working properly (I think).
                break
        else:
            #If we get here, we were able to send a byte to the address above.
            #That should probably not be possible, but if it is, it indicates the bus is working.
            break

    i2c.unlock()

def ScanI2c(i2c_bus, device_list):
    print("\nScanning I2C bus:")

    while not i2c_bus.try_lock():
        pass

    #One of the devices (the touch controller) does not respond unless we do this. Not sure why.
    try:
        #The address is invalid, so we need try/except. In theory, a valid address would preclude needing to do this, but it does not really matter.
        i2c_bus.writeto(0x00, b"")  #Address does not matter. Just need to put some clocks on the bus to get the device to show up.
    except:
        pass

    try:
        bus_devices = i2c_bus.scan()
        time.sleep(1)

    finally:  # unlock the i2c bus when ctrl-c'ing out of the loop
        i2c_bus.unlock()

        for found_device in bus_devices:
            DeviceFound = False
            for device_list_entry in device_list:
                if found_device == device_list_entry["address"]:
                    print(f"  found {device_list_entry["name"]} at address 0x{found_device:02X}")
                    DeviceFound = True
                    break
            if not DeviceFound:
                print(f"  found unknown device at address 0x{found_device:02X}")

        print("Done")

displayio.release_displays()

#Set up CPU hardware
i2c = board.I2C()                       #I2C Bus. uses board.SCL and board.SDA
ow_bus = OneWireBus(board.TX)           #One wire bus. Uses the board.TX pin
spi = board.SPI()                       #SPI bus. Uses SCK, MOSI, MISO
pixel = neopixel.NeoPixel(board.A0, 1) #Neopixel. Uses pin board.A0

#CPU Pins

GPIO_Pins = [digitalio.DigitalInOut(board.D5),
             digitalio.DigitalInOut(board.D6),
             digitalio.DigitalInOut(board.D9),
             digitalio.DigitalInOut(board.D10), ]

GPIO_Pins[0].switch_to_output(value=False)  #TODO: Temporary?

#LED high side control. On/off using this pin.
LED_HS = digitalio.DigitalInOut(board.A5)
LED_HS.switch_to_output(value=False)    #Active high

#LED low side control. Dim using this pin.
LED_LS = pwmio.PWMOut(board.RX, frequency=5000, duty_cycle=0)

#Interrupt pin for external hardware
#  Connects to both IO expanders and the eyeSPI connector
IOEXP_int = digitalio.DigitalInOut(board.D11)
IOEXP_int.switch_to_input(pull=digitalio.Pull.UP)

Buzzer = digitalio.DigitalInOut(board.A1)
Buzzer.switch_to_output(value=False)

LCD_Backlight = digitalio.DigitalInOut(board.A2)
LCD_Backlight.switch_to_output(value=True)    #Active high

ScanI2c(i2c, i2c_devices)
time.sleep(1)

#initialize display TODO: Probably need SD card init before this?
tft_cs = board.D12  #
tft_dc = board.A3   #
display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.A4)
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240)

#Initialize external hardware

#Initialize devices on the PCB
IOEXP1_dev = PCAL9555.PCAL9555(i2c, address=0x20)
IOEXP2_dev = PCAL9538.PCAL9538(i2c, address=0x70)
emc = EMC2101(i2c)
ds3231 = adafruit_ds3231.DS3231(i2c)

try:
    ft = adafruit_focaltouch.Adafruit_FocalTouch(i2c, debug=False)
except:
    i2c_unstick(i2c)
    print("No touch sensor present")

#Define Pins

#External Pins

#Relays:
Relays = [IOEXP1_dev.get_pin(2),
          IOEXP1_dev.get_pin(1),
          IOEXP1_dev.get_pin(0),
          IOEXP1_dev.get_pin(8) ]

for relay in Relays:
    relay.switch_to_output(value=False)

#Buttons
Buttons = {"up":     IOEXP1_dev.get_pin(3),
           "down":   IOEXP1_dev.get_pin(4),
           "left":   IOEXP1_dev.get_pin(5),
           "right":  IOEXP1_dev.get_pin(6),
           "center": IOEXP1_dev.get_pin(7) }

for button in Buttons:
    Buttons[button].switch_to_input(pull=digitalio.Pull.UP, invert_polarity=False)

IOEXP1_dev.set_int_pin(3, latch=False)
IOEXP1_dev.set_int_pin(4, latch=False)
IOEXP1_dev.set_int_pin(5, latch=False)
IOEXP1_dev.set_int_pin(6, latch=False)
IOEXP1_dev.set_int_pin(7, latch=False)

#GPIO 5. Planned to be used to control the misting system. Probably want a class for GPIOs eventually
GPIO5 = IOEXP1_dev.get_pin(9)
GPIO5.switch_to_output(value=False)

#HV Detect. This is connected thru a voltage divider to the 12V input power. The divider will act as a pull down when 12V is not present.
HV_Detect = IOEXP1_dev.get_pin(10)
HV_Detect.switch_to_input(pull=None, invert_polarity=False)
IOEXP1_dev.set_int_pin(10, latch=False) #Set interrupt on HV detect

#1-wire sensor control
OWI_Power = IOEXP1_dev.get_pin(14)
OWI_Fault = IOEXP1_dev.get_pin(13)      #Pulls to ground on power faults (over current or over temp)
OWI_Power.switch_to_output(value=False) #Has external pull-down to make sure it is off unless we want it on.
OWI_Fault.switch_to_input(pull=digitalio.Pull.UP, invert_polarity=True) #Low indicates a fault.
IOEXP1_dev.set_int_pin(13, latch=False) #Set interrupt on OWI fault
#TODO: I have seen CRC errors on the DS18b20 device. Catch these?
#Traceback (most recent call last):
#  File "code.py", line 141, in <module>
#  File "adafruit_ds18x20.py", line 90, in temperature
#  File "adafruit_ds18x20.py", line 123, in _read_temp
#  File "adafruit_ds18x20.py", line 139, in _read_scratch
#  File "adafruit_onewire/device.py", line 65, in readinto
#RuntimeError: CRC error."


#I2C sensor control
# The EN-I2C-DATA pin is not directly controlled. It is connected by an RC delay circuit to the EN-I2C-PWR pin.
TWI_Power = IOEXP2_dev.get_pin(2)
TWI_Fault = IOEXP2_dev.get_pin(3)   #Pulls to ground on power faults (over current or over temp)
TWI_Ready = IOEXP1_dev.get_pin(15)  #Pulls to ground when the I2C switch is off or not ready.

TWI_Power.switch_to_output(value=False) #Has external pull-down to make sure it is off unless we want it on.
TWI_Fault.switch_to_input(pull=digitalio.Pull.UP, invert_polarity=True) #Low indicates a fault.
TWI_Ready.switch_to_input(pull=digitalio.Pull.UP, invert_polarity=False)

IOEXP1_dev.set_int_pin(15, latch=False) #Set interrupt on TWI ready (I probably don't want this?)
IOEXP2_dev.set_int_pin(3, latch=False)  #Set interrupt on TWI power fault

#External GPIOs
 #Move GPIO5 here?
 #Make this a class?

GPIO_Power = IOEXP2_dev.get_pin(6)
GPIO_Fault = IOEXP2_dev.get_pin(7) #Pulls to ground on power faults (over current or over temp)

#High on these make them outputs
GPIO_DR = [IOEXP2_dev.get_pin(5),
           IOEXP2_dev.get_pin(4),
           IOEXP2_dev.get_pin(1),
           IOEXP2_dev.get_pin(0) ]

#GPIO_Pins = [digitalio.DigitalInOut(board.D5),
#             digitalio.DigitalInOut(board.D6),
#             digitalio.DigitalInOut(board.D9),
#             digitalio.DigitalInOut(board.D10), ]

GPIO_Power.switch_to_output(value=False) #Has external pull-down to make sure it is off unless we want it on.
GPIO_Fault.switch_to_input(pull=digitalio.Pull.UP, invert_polarity=True)    #Low indicates a fault.

for pin in GPIO_DR:
    pin.switch_to_output(value=False)   #Default to all inputs

for pin in GPIO_Pins:
    pin.switch_to_input(pull=None)   #Pins have pull ups on the external side. That should mean push-pull here without a pull up/down required. TODO: test this.

#End of initialization code
#---------------------------------------------------

#Register fan temp sensor
def emc_getdata(busdev, busID):
    return (busdev.internal_temperature*(9/5)+32)

IOT_dev.AddSensor(sensor.sensor(devClass=emc,
                                           devID="emc",
                                           Name="Fan Temp",
                                           UOM = "F",
                                           SensorClass="temperature",
                                           getdata_function=emc_getdata) )



'''
lib_ver: 00, chip_id: 06, firm_id: 00, vend_id: 11
ROM = ['0x28', '0x26', '0x1c', '0x80', '0xc', '0x0', '0x0', '0x25'] 	Family = 0x28
'''

'''
ROM:  bytearray(b'(\xd5x\xd9R \x01[')
ROM = ['0x28', '0xd5', '0x78', '0xd9', '0x52', '0x20', '0x1', '0x5b'] 	Family = 0x28

ROM:  bytearray(b'(&\x1c\x80\x0c\x00\x00%')
ROM = ['0x28', '0x26', '0x1c', '0x80', '0xc', '0x0', '0x0', '0x25'] 	Family = 0x28

40
38
28
128
12
0
0
37

'''

coreSN = bytearray([0x26, 0x1C, 0x80, 0x0C, 0x00, 0x00])

#Turn on OWI power and scan bus
OWI_Power.value = False
time.sleep(2)
OWI_Power.value = True
time.sleep(1)
ow_bus.reset()
devices = ow_bus.scan()

print("Found", len(devices), "devices on the 1-wire bus")

i=1
for device in devices:
    if device.serial_number == coreSN:
        IOT_dev.AddSensor(sensor.sensor(devClass=adafruit_ds18x20.DS18X20(ow_bus, device),
                                            devID="ds18b20",
                                            init_func=sensor.ds18b20_init,
                                            Name="CPU Temp",
                                            UOM = "F",
                                            SensorClass="temperature",
                                            getdata_function=sensor.ds18b20_getdata_F) )
    else:
        IOT_dev.AddSensor(sensor.sensor(devClass=adafruit_ds18x20.DS18X20(ow_bus, device),
                                            devID="ds18b20",
                                            init_func=sensor.ds18b20_init,
                                            Name="DS Temp " + str(i),
                                            UOM = "F",
                                            SensorClass="temperature",
                                            getdata_function=sensor.ds18b20_getdata_F) )
        i = i+1

#Turn on TWI power and scan bus
TWI_Power.value = True
time.sleep(1)

try:
    sht = adafruit_sht4x.SHT4x(i2c)
except:
    i2c_unstick(i2c)
    print("No SHT40 device detected")
else:
    IOT_dev.AddSensor(sensor.sensor(devClass=sht,
                                    devID="sht",
                                    Name="sht temp",
                                    UOM = "F",
                                    SensorClass="temperature",
                                    getdata_function=sht_temp_getdata) )

    IOT_dev.AddSensor(sensor.sensor(devClass=sht,
                                    devID="sht",
                                    Name="sht humidity",
                                    UOM = "%",
                                    SensorClass="humidity",
                                    getdata_function=sht_humid_getdata) )




IOT_dev.AddBinarySensor(sensor.sensor(devClass=Relays[0],
                                      devID="binary",
                                      Name="Relay 0",
                                      UOM = "",
                                      SensorClass="power",
                                      getdata_function=sensor.gpio_getdata) )

IOT_dev.AddBinarySensor(sensor.sensor(devClass=Relays[1],
                                      devID="binary",
                                      Name="Relay 1",
                                      UOM = "",
                                      SensorClass="power",
                                      getdata_function=sensor.gpio_getdata) )

IOT_dev.AddBinarySensor(sensor.sensor(devClass=Relays[2],
                                      devID="binary",
                                      Name="Relay 2",
                                      UOM = "",
                                      SensorClass="power",
                                      getdata_function=sensor.gpio_getdata) )

IOT_dev.AddBinarySensor(sensor.sensor(devClass=Relays[3],
                                      devID="binary",
                                      Name="Relay 3",
                                      UOM = "",
                                      SensorClass="power",
                                      getdata_function=sensor.gpio_getdata) )

#sensor_list.CaptureData()
#print("CPU Temp:", sensor_list.GetCurrentVal("cpu_temp"))
#print("DS1 Temp:", sensor_list.GetCurrentVal("ds_temp_1"))
#time.sleep(1)
#sensor_list.ListSensors()

GPIO_Power.value = True
TWI_Power.value = True
i = 0

#Set GPIOs as output
GPIO_DR[0].value = True
GPIO_DR[1].value = True
GPIO_DR[2].value = True
GPIO_DR[3].value = True

GPIO_Pins[0].switch_to_output(value=False)
GPIO_Pins[1].switch_to_output(value=False)
GPIO_Pins[2].switch_to_output(value=False)
GPIO_Pins[3].switch_to_output(value=False)

emc.manual_fan_speed = 100
#print(ds3231.datetime)
#ds3231.datetime = time.struct_time((2017, 1, 1, 0, 0, 0, 6, 1, -1))
#print(ds3231.datetime)


def Wifi_onconnect(DebugDevices, Messages):
    print("Connecting to SSID: {0:s}...".format(Messages[0]), end =".")
    DebugDevices["pixel"][0]= (255, 255, 0)
    #return number

def wifi_onok(DebugDevices, Messages):
    print("ok")
    print("  IP: ", Messages[0])
    DebugDevices["pixel"][0]= (0, 0, 0)

def wifi_onfail(DebugDevices, Messages):
    print("Failed ({0:d}/{1:d}). Error: ".format(Messages[1], Messages[2]), Messages[0])
    DebugDevices["pixel"][0]= (255, 0, 0)

def MQTT_onconnect(DebugDevices, Messages):
    print("Connecting to MQTT broker at %s..." % Messages[0], end =".")
    DebugDevices["pixel"][0]= (0, 0, 255)

def MQTT_onok(DebugDevices, Messages):
    print("ok")
    DebugDevices["pixel"][0]= (0, 0, 0)

def MQTT_onerror(DebugDevices, Messages):
    print("Failed ({0:d}/{1:d}). Error:".format(Messages[1], Messages[2]), Messages[0])
    DebugDevices["pixel"][0]= (255, 0, 0)

def NTP_onconnect(DebugDevices, Messages):
    print("Getting time...", end =".")
    DebugDevices["pixel"][0]= (128, 0, 128)

def NTP_onerror(DebugDevices, Messages):
    print("Failed to get time from NTP. Error ({0:d}/{1:d}):".format(Messages[1], Messages[2]), Messages[0])
    DebugDevices["pixel"][0]= (255, 0, 0)

def NTP_onok(DebugDevices, Messages):
    print("ok")
    print(f'Time set to {Messages[0].tm_mon:02d}/{Messages[0].tm_mday:02d}/{Messages[0].tm_year:04d} {Messages[0].tm_hour:02d}:{Messages[0].tm_min:02d}:{Messages[0].tm_sec:02d}')
    DebugDevices["pixel"][0]= (0, 0, 0)


time.sleep(1)
pixel[0] = (0, 0, 255)
time.sleep(1)


IOT_dev.AddDebugDev(pixel, "pixel")
IOT_dev.WiFiConnectStart = Wifi_onconnect
IOT_dev.WiFiConnectOK = wifi_onok
IOT_dev.WiFiConnectError = wifi_onfail
IOT_dev.MQTTConnectStart = MQTT_onconnect
IOT_dev.MQTTConnectOK = MQTT_onok
IOT_dev.MQTTConnectError = MQTT_onerror

IOT_dev.NTPConnectStart = NTP_onconnect
IOT_dev.NTPConnectOK = NTP_onok
IOT_dev.NTPConnectError = NTP_onerror

IOT_dev.ConnectToNetwork()
IOT_dev.GetTimeFromNTP()

'''
TODO: had this error when sending MQTT data, see if I can handle it somehow.

Traceback (most recent call last):
  File "code.py", line 473, in <module>
  File "/lib/iot_device/iot_device.py", line 324, in SendSensorValues
  File "adafruit_minimqtt/adafruit_minimqtt.py", line 636, in publish
OSError: [Errno 113] ECONNABORTED
'''


#1-wire sensor ROM = ['0x28', '0x26', '0x1c', '0x80', '0xc', '0x0', '0x0', '0x25'] 	Family = 0x28
#print("1-wire sensor addr: ", ds18b20.address.rom)
#print("1-wire sensor ROM = {} \tFamily = 0x{:02x}".format([hex(i) for i in ds18b20.address.rom], ds18b20.address.family_code))
#print("1-wire sensor SN = {} \tFamily = ", ds18b20.address.serial_number)

#sensor_list["board temp"] = 1
#coreSN = bytearray([0x26, 0x1C, 0x80, 0x0C, 0x00, 0x00])

'''use this code to rescan the one wire bus. The reset and sleep functions seem to be required.
ow_bus.reset()
time.sleep(1)
devices = ow_bus.scan()

for device in devices:
    print("sn:", device.serial_number)

print("done with sn")
time.sleep(10)

#BUFF:  bytearray(b'P\x05KF\x7f\xff\x0c\x10\x1c')
#BUFF:  bytearray(b'P\x05KF\x7f\xff\x0c\x10\x1c')
#BUFF:  bytearray(b'P\x05KF\x7f\xff\x0c\x10\x1c')
#BUFF:  bytearray(b'S\x01KF\x7f\xff\x0c\x10-')

time.sleep(10)
'''

'''
#Test display
# Make the display context
splash = displayio.Group()
display.show(splash)
#display.root_group = splash

# Draw a green background
color_bitmap = displayio.Bitmap(320, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x00FF00  # Bright Green

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)

splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(280, 200, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0xAA0088  # Purple
inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=20, y=20)
splash.append(inner_sprite)

# Draw a label
text_group = displayio.Group(scale=3, x=57, y=120)
text = "Hello World!"
text_area = label.Label(terminalio.FONT, text=text, color=0xFFFF00)
text_group.append(text_area)  # Subgroup for text scaling
splash.append(text_group)

#End of display test
'''

IOT_dev.CaptureData()
IOT_dev.SendSensorValues()

Relays[0].value = False
LCD_Backlight.value = False


now = time.localtime()
OldMin = now.tm_min
i = 0

#timer_dev.ShowEventTable()
print(timer_dev.GetCurrentState(now))

NowStates = timer_dev.GetCurrentState(now)
for NowState in NowStates:
    if NowState == "heatlamp":
        Relays[1].value = NowStates[NowState]
    elif NowState == "uv":
        Relays[0].value = NowStates[NowState]
    elif NowState == "led":
        if NowStates[NowState]:
            #LEDs on
            LED_HS.value = True
            LED_LS.duty_cycle = 65535
        else:
            LED_HS.value = False
            LED_LS.duty_cycle = 0

ThermostatSetpoint = 80


gc.collect()
print("Free Memory:", gc.mem_free(), "bytes")

while True:
    now = time.localtime()

    if now.tm_min != OldMin:
        OldMin = now.tm_min
        IOT_dev.CaptureData()
        NowStates = timer_dev.GetCurrentState(now)
        
        #Debug outputs
        print("--------------")
        print(f"{now.tm_mon:02d}/{now.tm_mday:02d}/{now.tm_year:04d} {now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}" )
        print("Current State: ", NowStates)
        #IOT_dev.PrintSensorValues()
        
        #Handle thermostat functions. TODO: should this be in the IOT class?
        ThermostatTemp = IOT_dev.GetSensorValue("ds_temp_1")
        print("TSTAT Temp: ", ThermostatTemp)
        if (ThermostatTemp is None) or (NowStates['tstat']['value'] is False):
            #We don't have a temp from the temp sensor, or the event is false. Turn off the heater.
            Relays[3].value = False
        elif ThermostatTemp > NowStates['tstat']['value']:
            #Temperature above setpoint, turn off heater.
            Relays[3].value = False
        else:
            #Temperature below setpoint, turn on heater.
            Relays[3].value = True

        Relays[1].value = NowStates['heatlamp']['value']
        Relays[0].value = NowStates['uv']['value']
        if NowStates['led']['value']:
            #LEDs on
            LED_HS.value = True
            LED_LS.duty_cycle = 65535
        else:
            #LEDs off
            LED_HS.value = False
            LED_LS.duty_cycle = 0
        
        #TODO: Relay updates in this loop won't show up when we call SendSensorValues on this iteration.
        # This is because they are determined when CaptureData is called before the relays are updated. 
        # The data sent to the MQTT server may be delayed by 1 min. Do I care?
        IOT_dev.SendSensorValues()

    time.sleep(.2)
#---------------------------------------------------------------------------------------------------
i = 0

while True:
    i = i+1
    if i > 10:
        i = 0
    print(i)

    time.sleep(1)