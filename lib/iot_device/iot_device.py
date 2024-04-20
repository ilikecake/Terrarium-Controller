
import json
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



class iot_device:
    def __init__(self):
        #TODO: Read all data from the config file into private variables
        self._TimeoutCounts = 200     #How many times to try connecting to Wifi and MQTT before reset.
        self._RetryDelay = 30         #How long to wait between retries of wifi and MQTT connection. Note that the connect functions also have delay built in, so real delay will be longer than this.
        self._NTP_Time_Set = False    #Set to True when a valid time was recieved from NTP
        self._NetworkConnected = False
        self._ConnectedToBroker = False

        self._UUID = secrets["MQTT_Device_info"]["ids"][0]
        self._Name = secrets["device_ID"]   #TODO: Make this calculated from the readable name?
        self._ReadableName = secrets["MQTT_Device_info"]["name"]
        
        self._MQTT_Device_Info = secrets["MQTT_Device_info"]
        self._MQTT_State_Topic = "homeassistant/sensor/" + self._UUID + "/state"
        self._MQTT_lwt = "homeassistant/sensor/" + self._UUID + "_" + self._Name + "/lwt"  

        self._pool = socketpool.SocketPool(wifi.radio)
        self._ssl_context = ssl.create_default_context()
        
        self._SendDataTimeout = 5   #Set to zero to disable retry on sending data.
        
        
        self._NumSensors = 0
        self._NumBinarySensors = 0
        self._SensorListDict = {}
        self._BinarySensorListDict = {}
        
        wifi.radio.hostname = self._Name    #TODO: make sure that this is an allowable hostname (only alphabetic characters (A-Z), numeric characters (0-9), the minus sign (-), and the period (.))

        # Set up a MiniMQTT Client
        self._mqtt_client = MQTT.MQTT(broker=secrets["mqtt_broker_ip"],
                                      port=int(secrets["mqtt_broker_port"]),
                                      username=secrets["mqtt_broker_user"],
                                      password=secrets["mqtt_broker_pass"],
                                      socket_pool=self._pool,
                                      ssl_context=self._ssl_context, )

        self._dbg_dev = {}
        self._WiFiConnectStart = None
        self._WiFiConnectOK = None
        self._WiFiConnectError = None
        
        self._MQTTConnectStart = None
        self._MQTTConnectOK = None
        self._MQTTConnectError = None
        
        self._NTPConnectStart = None
        self._NTPConnectOK = None
        self._NTPConnectError = None
        
        self._UseDST = True
        self._DSTApplied = False


    #TODO: Make sure this does not take too long to fail out, or make another (sorta) non-blocking network connect. We want the device to function without a network present.
    def ConnectToNetwork(self):
        Retries = 0

        while Retries < self._TimeoutCounts:
            Retries = Retries + 1

            if wifi.radio.ipv4_address is None:
                #Not connected to wifi
                if self._WiFiConnectStart is not None:
                    self._WiFiConnectStart(self._dbg_dev, [secrets["ssid"]])
                try:
                    #print("con")
                    wifi.radio.connect(secrets["ssid"], secrets["password"])
                    #print("con2")
                except Exception as e:  # pylint: disable=broad-except
                    if self._WiFiConnectError is not None:
                        self._WiFiConnectError(self._dbg_dev, [e, Retries, self._TimeoutCounts])
                    time.sleep(self._RetryDelay)
                else:
                    if wifi.radio.ipv4_address is not None:
                        self._NetworkConnected = True
                        if self._WiFiConnectOK is not None:
                            self._WiFiConnectOK(self._dbg_dev, [wifi.radio.ipv4_address])
                        Retries = Retries - 1   #Wifi is connected, but MQTT won't try to connect until the next time through the loop.
            else:
                #Connected to wifi, try to connect to MQTT
                if self._MQTTConnectStart is not None:
                        self._MQTTConnectStart(self._dbg_dev, [self._mqtt_client.broker])

                try:
                    self._mqtt_client.connect()        #This command has a built in retry/timeout, so it takes about 3 min to fail.
                    self.SendDiscovery()               #Make this private eventually
                except Exception as e:  # pylint: disable=broad-except
                    if self._MQTTConnectError is not None:
                        self._MQTTConnectError(self._dbg_dev, [e, Retries, self._TimeoutCounts])
                    time.sleep(self._RetryDelay)     #Note: there is a delay/retry built into the connect function also, so this will take longer than you think.
                else:
                    #We are connected to wifi and the MQTT broker.
                    self._ConnectedToBroker = True
                    if self.MQTTConnectOK is not None:
                        self.MQTTConnectOK(self._dbg_dev, [])
                    return
        #If we get here, the timeout count is reached. Hard reset the device.
        print("This is not working, reset the device.")
        microcontroller.reset()

    def GetTimeFromNTP(self, SilentMode = False):
        #global DST_is_applied
        NTP_Retries = 5
        NTP_Retry_Delay = 1     #sec
        Retries = 0

        if secrets["NTP_ip"] is '':
        #TODO: silent mode here
            print("Skipping time setup")
            return False

        if SilentMode == False:
            if self._NTPConnectStart is not None:
                        self._NTPConnectStart(self._dbg_dev, [])

        while True:
            if Retries > NTP_Retries:
                #if we get here, NTP time sync failed
                
                print("skipped")
                return False
            else:
                Retries = Retries + 1

            try:
                TZ_OFFSET = int(secrets["timezone"]) # time zone offset in hours from UTC
                ntp = adafruit_ntp.NTP(self._pool, server=secrets["NTP_ip"], tz_offset=TZ_OFFSET)
                self._DSTApplied = -1
                now = self.HandleDST(ntp.datetime)    #disable for now

            except Exception as e:  # pylint: disable=broad-except
                #print("Failed to get time from NTP. Error ({0:d}/{1:d}):".format(Retries, NTP_Retries), e)
                if SilentMode == False:
                    if self._NTPConnectError is not None:
                        self._NTPConnectError(self._dbg_dev, [e, Retries, NTP_Retries])
                #if SilentMode == False:
                #    TheDisplay.StatusText(2,"Failed ({0:d}/{1:d})".format(Retries, NTP_Retries))
                #    TheDisplay.StatusText(3,e)
                time.sleep(NTP_Retry_Delay)
            else:
                if SilentMode == False:
                    if self._NTPConnectOK is not None:
                        self._NTPConnectOK(self._dbg_dev, [now])
                #if SilentMode == False:
                    #pixel.fill((0, 0, 0))  #Off
                #print("ok")
                #print("Time is:", now)
                rtc.RTC().datetime = now
                return True

    def HandleDST(self, now):
        #Call periodically to check if DST is active and update the RTC if needed.
        #   This function should be called by GetTimeFromNTP to determine if DST should be applied to the RTC time.
        #   This fucntion should also be called periodically from the main loop to change the time with DST starts and ends.
        #
        #   Note that the 'tm_isdst' part of the time struct is not implemented, so we have a separate global variable (DST_is_applied) to track
        #   if DST is applied.
        #
        #   In the U.S., daylight saving time starts on the second Sunday
        #   in March and ends on the first Sunday in November, with the time
        #   changes taking place at 2:00 a.m. local time.
        #
        #TODO: This function corrects the date/time struct but does not update the RTC.
        
        corrected_time_struct = None
        corrected_time = time.mktime(now)

        if self.IsDST(now):
            #is DST
            if (self._DSTApplied == 1):
                #DST already applied, nothing to do.
                return now
            else:
                #Time was not DST, but should be. Add 1 hour.
                corrected_time = corrected_time + 3600
                self._DSTApplied = 1
        else:
            #not DST
            if (self._DSTApplied == 0):
                #DST is not applied, nothing to do.
                return now
            elif (self._DSTApplied == 1):
                #Time was DST, but is not anymore. Subtract 1 hour.
                corrected_time = corrected_time - 3600
                self._DSTApplied = 0
            else:
                #Time is not DST, but tm_isdst is not set. Set it to 0. Do not change time.
                self._DSTApplied = 0

        #Return the corrected time
        corrected_time_struct = time.localtime(corrected_time)
        return corrected_time_struct
    
    def IsDST(self, now):
        '''Returns True if the given date should have daylight savings time applied.
    
            TODO: Should this be in the class, or just a helper function?
        '''
        if ((now.tm_mon > 3) and (now.tm_mon < 11)) or                                          \
           ((now.tm_mon == 3) and (now.tm_mday - now.tm_wday >= 8) and (now.tm_hour >= 2)) or   \
           ((now.tm_mon == 11) and (now.tm_mday - now.tm_wday <= 0) and (now.tm_hour >= 2)):
            #is DST
            return True
        return False
    
    def SendDiscovery(self):
        #Subscriptions
        #mqtt_client.subscribe(MQTT_Light_topic, qos=1)
        #mqtt_client.subscribe(MQTT_Remote_Data_Topic, qos=1)
        #mqtt_client.subscribe(MQTT_Light_Command_Topic, qos=1)
        
        #Last will
        self._mqtt_client.publish(self._MQTT_lwt, 'online', qos=1, retain=True)  
    
        #Sensors
        for sensor in self._SensorListDict:
            SensorID = self._UUID + "_" + self._SensorListDict[sensor].Name
            MQTT_Config = "homeassistant/sensor/" + SensorID + "/config"
            MQTT_Config_Payload =   json.dumps({"device_class":           self._SensorListDict[sensor].Class,                        \
                                                "name":                   self._SensorListDict[sensor].ReadableName,                 \
                                                "state_topic":            self._MQTT_State_Topic,                               \
                                                "unit_of_measurement":    self._SensorListDict[sensor].Units,                        \
                                                "value_template":         "{{value_json."+self._SensorListDict[sensor].Name+"}}",    \
                                                "unique_id":              SensorID,                                                 \
                                                "availability_topic":     self._MQTT_lwt,                                       \
                                                "payload_available":      "online",                                             \
                                                "payload_not_available":  "offline",                                            \
                                                "device":                 self._MQTT_Device_Info })
            self._mqtt_client.publish(MQTT_Config, MQTT_Config_Payload, qos=1, retain=True)
            
        for sensor in self._BinarySensorListDict:
            SensorID = self._UUID + "_" + self._BinarySensorListDict[sensor].Name
            MQTT_Config = "homeassistant/binary_sensor/" + SensorID + "/config"
            MQTT_Config_Payload =   json.dumps({"device_class":           self._BinarySensorListDict[sensor].Class,                     \
                                                "name":                   self._BinarySensorListDict[sensor].ReadableName,              \
                                                "state_topic":            self._MQTT_State_Topic,                                       \
                                                "value_template":         "{{value_json."+self._BinarySensorListDict[sensor].Name+"}}", \
                                                "payload_on":             True,                                                         \
                                                "payload_off":            False,                                                        \
                                                "unique_id":              SensorID,                                                     \
                                                "availability_topic":     self._MQTT_lwt,                                               \
                                                "payload_available":      "online",                                                     \
                                                "payload_not_available":  "offline",                                                    \
                                                "device":                 self._MQTT_Device_Info })
            self._mqtt_client.publish(MQTT_Config, MQTT_Config_Payload, qos=1, retain=True)
      
        #Lights
        #mqtt_client.publish(MQTT_Config_light, MQTT_Config_Light_Payload, qos=1, retain=True)
        
        #Buttons
        #mqtt_client.publish(MQTT_Config_Upper_Button, MQTT_Config_Upper_Button_Payload, qos=1, retain=True)
        #mqtt_client.publish(MQTT_Config_Lower_Button, MQTT_Config_Lower_Button_Payload, qos=1, retain=True)

    def RemoveMQTT():
        #Sends empty config packets to home assistant. This tells home assistant to delete these sensors from its config.
        #Should never be called, but I am saving this here in case it is needed for debug.
        print("Delete the MQTT sensor")
        
        #Sensors
        for sensor in self._SensorListDict:
            SensorID = self._UUID + "_" + self._SensorListDict[sensor].Name
            MQTT_Config = "homeassistant/sensor/" + SensorID + "/config"
            self._mqtt_client.publish(MQTT_Config, '', qos=1, retain=True)
        #Binary sensors
        #Lights
        #Buttons

    #Sensor handling functions
    def AddSensor(self, SensorToAdd, ToInit = False):
        #TODO: check if the sensor name already exsists.
        self._SensorListDict[SensorToAdd.Name] = SensorToAdd
        self._NumSensors = self._NumSensors + 1
        if ToInit:
            self._SensorListDict[SensorToAdd.Name].Initialize()
        #TODO: Get inital value from sensor here?

    def RemoveSensor(self, SensorName):
        #TODO: What happens if the sensor name does not exist?
        #TODO: Send removal packet over MQTT when a sensor is removed
        del self._SensorListDict[SensorName]
        
    def AddBinarySensor(self, SensorToAdd, ToInit = False):
        #TODO: check if the sensor name already exsists.
        self._BinarySensorListDict[SensorToAdd.Name] = SensorToAdd
        self._NumBinarySensors = self._NumBinarySensors + 1
        if ToInit:
            self._BinarySensorListDict[SensorToAdd.Name].Initialize()
        #TODO: Get inital value from sensor here?

    def RemoveBinarySensor(self, SensorName):
        #TODO: What happens if the sensor name does not exist?
        #TODO: Send removal packet over MQTT when a sensor is removed
        del self._BinarySensorListDict[SensorName]

    def ListSensors(self):
        #TODO: Add binary sensors
        SensorList = []
        #print("Sensor List:")
        for sensor in self._SensorListDict:
            SensorList.append(sensor)
            #print(sensor)
        return SensorList

    def CaptureData(self):
        #Get new values from all sensors
        for SensorName in self._SensorListDict:
            self._SensorListDict[SensorName].GetData
        for SensorName in self._BinarySensorListDict:
            self._BinarySensorListDict[SensorName].GetData
            
    def PrintSensorValues(self):
        #Does not query the sensor for a new value.
        for SensorName in self._SensorListDict:
            print(self._SensorListDict[SensorName].Name, ":", self._SensorListDict[SensorName].CurrentVal)
            
        for SensorName in self._BinarySensorListDict:
            print(self._BinarySensorListDict[SensorName].Name, ":", self._BinarySensorListDict[SensorName].CurrentVal)

    def SendSensorValues(self):
        #Does not query the sensor for a new value.
        ValuesToSend = {}
        for SensorName in self._SensorListDict:
            ValuesToSend[SensorName] = self._SensorListDict[SensorName].CurrentVal
        for SensorName in self._BinarySensorListDict:
            ValuesToSend[SensorName] = self._BinarySensorListDict[SensorName].CurrentVal
        print(ValuesToSend)
        
        #TODO: not sure if it is possible for this to fail. I don't think the device checks to see if the server recieved the data.
        for x in range(self._SendDataTimeout+1):
            try:
                self._mqtt_client.publish(self._MQTT_State_Topic, json.dumps(ValuesToSend))     #TODO: Add a try/catch here?
            except OSError as e: #TODO: what type of exception do I catch here?
                print("Send failed:", e)
            else:
                return
                
                
    def GetSensorValue(self, SensorName):
        return self._SensorListDict[SensorName].CurrentVal

        '''
        When server is disconnected, leave network port disconnected for a while:
        after a few min:
            Send failed: [Errno 11] EAGAIN  <-- this happens for a while (5 min)
            
            *then*
            
            Send failed: [Errno 113] ECONNABORTED
            Send failed: [Errno 128] ENOTCONN
            Send failed: 32
            Send failed: 32
            
            *send failed 32 keeps happening therafter.
            *it appears these commends fail immediately
        '''
        
        
        '''
        {'relay_1': False, 'ds_temp_1': 19.875, 'relay_0': False, 'fan_temp': 26, 'relay_3': False, 'relay_2': False}
        Traceback (most recent call last):
         File "code.py", line 635, in <module>
         File "/lib/iot_device/iot_device.py", line 379, in SendSensorValues
         File "adafruit_minimqtt/adafruit_minimqtt.py", line 636, in publish
        OSError: [Errno 104] ECONNRESET
        '''
        

    def GetCurrentVal(self, SensorName):
        #Return the latest saved value from the sensor. Does not query the sensor for a new value.
        return self._SensorListDict[SensorName]._CurrentValue


    def AddDebugDev(self, Dev, DevName):
        self._dbg_dev[DevName] = Dev

    @property
    def WiFiConnectStart(self):
        return self._WiFiConnectStart

    @WiFiConnectStart.setter
    def WiFiConnectStart(self, func):
        self._WiFiConnectStart = func 

    @property
    def WiFiConnectOK(self):
        return self._WiFiConnectOK

    @WiFiConnectOK.setter
    def WiFiConnectOK(self, func):
        self._WiFiConnectOK = func
        
    @property
    def WiFiConnectError(self):
        return self._WiFiConnectError

    @WiFiConnectError.setter
    def WiFiConnectError(self, func):
        self._WiFiConnectError = func

    @property
    def MQTTConnectStart(self):
        return self._MQTTConnectStart

    @MQTTConnectStart.setter
    def MQTTConnectStart(self, func):
        self._MQTTConnectStart = func
    
    @property
    def MQTTConnectOK(self):
        return self._MQTTConnectOK

    @MQTTConnectOK.setter
    def MQTTConnectOK(self, func):
        self._MQTTConnectOK = func
        
    @property
    def MQTTConnectError(self):
        return self._MQTTConnectError

    @MQTTConnectError.setter
    def MQTTConnectError(self, func):
        self._MQTTConnectError = func
        
    @property
    def NTPConnectStart(self):
        return self._NTPConnectStart

    @NTPConnectStart.setter
    def NTPConnectStart(self, func):
        self._NTPConnectStart = func
    
    @property
    def NTPConnectOK(self):
        return self._NTPConnectOK

    @NTPConnectOK.setter
    def NTPConnectOK(self, func):
        self._NTPConnectOK = func
        
    @property
    def NTPConnectError(self):
        return self._NTPConnectError

    @NTPConnectError.setter
    def NTPConnectError(self, func):
        self._NTPConnectError = func
        