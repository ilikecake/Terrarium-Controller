
#import json
import time
#import board
#import digitalio
import rtc
#import displayio
import adafruit_ntp
#import countio
import microcontroller

import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests
import adafruit_minimqtt.adafruit_minimqtt as MQTT

try:
    from iot_device.secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise   #TODO: What does this do?

#Name
#ReadableName
#Device Class
#UoM

'''
MQTT_Config_Temp_Payload = json.dumps({"device_class":           "temperature",                             \
                                       "name":                   secrets["device_name"] + " Temperature",   \
                                       "unit_of_measurement":    "°F",                                      \
                                       "value_template":         "{{value_json.temperature}}",              \
                                       "unique_id":              secrets["UUID"]+"_temp",                   \
'''
'''class SensorList:
    def __init__(self):
        self._NumSensors = 0
        self._SensorListDict = {}   #Dictionary of the sensors

    def AddSensor(self, SensorToAdd, ToInit = False):
        #TODO: check if the sensor name already exsists.
        self._SensorListDict[SensorToAdd.Name] = SensorToAdd
        self._NumSensors = self._NumSensors + 1
        if ToInit:
            self._SensorListDict[SensorToAdd.Name].Initialize()
        #TODO: Get inital value from sensor here?

    def RemoveSensor(self, SensorName):
        #TODO: What happens if the sensor name does not exist?
        del self._SensorListDict[SensorName]

    def ListSensors(self):
        SensorList = []
        #print("Sensor List:")
        for sensor in self._SensorListDict:
            SensorList.append(sensor)
            #print(sensor)
        return SensorList

    def CaptureData(self):
        #Get new values from the sensors
        for SensorName in self._SensorListDict:
            self._SensorListDict[SensorName].GetData
            
    def PrintSensorValues(self):
        #Does not query the sensor for a new value.
        for SensorName in self._SensorListDict:
            print(self._SensorListDict[SensorName].Name, ":", self._SensorListDict[SensorName].CurrentVal)

    def GetCurrentVal(self, SensorName):
        #Return the latest saved value from the sensor. Does not query the sensor for a new value.
        return self._SensorListDict[SensorName]._CurrentValue
'''

class sensor:
    def __init__(self, devClass, devID, Name, SensorClass, UOM = None, init_func = None, getdata_function = None):
        self._DevClass = devClass
        self._DevID = devID
        
        self._ReadableName = Name.strip()   #TODO: Make readable name and name both enterable and format the names accordingly
        self._Name = self._ReadableName.replace(" ", "_").lower()   #Must be unique for the device.
        self._Units = UOM   #TODO: check units somehow
        self._SensorClass = SensorClass     #TODO: make this consistent with the list from home assistant (https://developers.home-assistant.io/docs/core/entity/sensor/)
        self._CurrentValue = 0
        
        self._GetData = getdata_function
        self._Init = init_func
        
        #Init function can be empty if the sensor does not require any initialization
        if self._Init is not None:
            self._Init(self._DevClass, self._DevID)
        
        #print("Readable Name:", self._ReadableName)
        #print("Name:", self._Name)
    
    '''Probably can't do this here, do this at the IOT_Device level
    def GenerateMQTTDiscoveryPacket(self, UUID, DeviceName):
        return json.dumps({"device_class":           self._SensorClass,                         \
                           "name":                   DeviceName + self._ReadableName,           \
                           "state_topic":            "homeassistant/sensor/" + UUID + "/state", \
                           "unit_of_measurement":    self._Units,                               \
                           "value_template":         "{{value_json."+self._Name+"}}",           \
                           "unique_id":              UUID + "_" + self._Name,                   \
                           "availability_topic":     MQTT_lwt,                                  \
                           "payload_available":      "online",                                  \
                           "payload_not_available":  "offline",                                 \
                           "device":                 MQTT_Device_info                           })
    '''
    
    
    
    @property
    def Initialize(self):
        if self._Init is not None:
            return self._Init(self._DevClass, self._DevID)

    @Initialize.setter
    def Initialize(self, func):
        self._Init = func
    
    @property
    def GetData(self):
        self._CurrentValue = self._GetData(self._DevClass, self._DevID)
        return self._CurrentValue

    @GetData.setter
    def GetData(self, func):
        self._GetData = func
        
    @property
    def CurrentVal(self):
        #Read only
        return self._CurrentValue
        
    @property
    def Name(self):
        #Read only
        return self._Name
        
    @property
    def Class(self):
        #Read only
        return self._SensorClass
        
    @property
    def ReadableName(self):
        #Read only
        return self._ReadableName
        
    @property
    def Units(self):
        #Read only
        return self._Units
        
        
        
#Sensor specific functions
def BlankFunction(busdev, busID):
    pass

def ds18b20_init(busdev, busID):
    #Read the sensor value 5 times. It appears that the first few values read 
    # from the device can be bad
    for i in range(5):
        try:
            temp = busdev.temperature
        except RuntimeError:
            pass
    return

def ds18b20_getdata_C(busdev, busID):
    for i in range(10):
        try:
            temp = busdev.temperature
            return temp
        except RuntimeError as e:
            print(i+1, "of 10:", e)
            pass
    return 0    #If we get here, we had 5 consecutive read failures.
    
def ds18b20_getdata_F(busdev, busID):
    for i in range(10):
        try:
            temp = busdev.temperature
            return (temp*(9/5))+32
        except RuntimeError as e:
            print(i+1, "of 10:", e)
            pass
    return 0    #If we get here, we had 5 consecutive read failures.
    
def gpio_getdata(busdev, busID):
    return busdev.value