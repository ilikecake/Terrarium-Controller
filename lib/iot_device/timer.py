from adafruit_datetime import time as time_obj
import time

#TODO: Handle both time and datetime


class timer:
    def __init__(self):
        #TODO: Read all data from the config file into private variables
        self._OutputList = []
        self._EventList = [{"time": time_obj(0, 0)}]

    def AddOutput(self, OutputToAdd):
        #TODO: check if output is already in the list, make sure output is a string.
        self._OutputList.append(OutputToAdd)
        self._OutputList.sort() #TODO: I dont think I need this.
        
    def DisplayOutputs(self):
        print(self._OutputList)
        
    def AddEvent(self, EventToAdd):
        #TODO: Do not allow events at 00:00 <--- not needed, but we should check for calculated events.
        
        #Make sure the event has a 'time' key
        if not ('time' in EventToAdd):
            raise NameError("The key 'time' must be in the dictionary")
        
        #Check if there are keys in the event that dont correspond to outputs. If so, raise an error.
        UnknownItems = [k for k in EventToAdd.keys() if k not in self._OutputList]
        if len(UnknownItems) > 1:
            UnknownItems.remove('time')
            raise ValueError(f"Unknown item(s) in event: {UnknownItems}")
        
        #Make sure time is in the right format. We can support time or time_struct.
        if isinstance(EventToAdd['time'], time.struct_time):
            #We are given a time in time_struct format. Sorting of time_struct objects is not 
            #supported. Convert to a time object.
            TimeToAdd = time_obj(EventToAdd['time'].tm_hour, EventToAdd['time'].tm_min)
            EventToAdd['time'] = TimeToAdd
        elif not isinstance(EventToAdd['time'], time_obj):
            #We are not given either a time or time_struct object.
            raise TypeError('Time must be a time or time_struct object')
        self._EventList.append(EventToAdd)
        self._EventList.sort(key=lambda val: val['time'])
        
    def ShowEventList(self, ShowRaw = False):
        NameLength = 4
        ValLength = 7
        
        if ShowRaw:
            print(self._EventList)
        else:
            for event in self._EventList:
                for key in event:
                    if len(key) > NameLength:
                        NameLength = len(key)
            
            NameLength = NameLength+1
            
            EventTimes = [k['time'] for k in self._EventList]
            EventNameStr = '{:<'+str(NameLength)+'}|'
            ValStr = '{: ^'+str(ValLength)+'}|'
            line = EventNameStr.format('time')
            
            for event in self._EventList:
                TimeStr = '{:02d}:{:02d}'.format(event['time'].hour, event['time'].minute)
                line = (line + ValStr).format(TimeStr)
            
            Seperator = ''
            for i in range (0, len(line)):
                Seperator = Seperator + '-'
            
            print(Seperator)
            print(line)
            print(Seperator)
            
            for output in self._OutputList:
                line = EventNameStr.format(output)
                for event in self._EventList:
                    try:
                        if event[output]['type'] == 'calc':
                            line = line + ValStr.format(' ')
                        else:
                            #TODO: In the future we can probably add other if/else statements here to handle more complicated events.
                            line = line + ValStr.format(event[output]['value'])
                    except KeyError:
                        line = line + ValStr.format(event[output]['value'])
                print(line)
                print(Seperator)
        
    def GenerateEventTable(self):
        #TODO: Handle if either the output list or event list is blank.
        #TODO: What do we do if something is in the output list but not in the event list, what about the opposite?
        #TODO: Handle repeated events
        #TODO: WHat if an output is in the output list but not in any events?
        #print("Event List:")
        #print(self._EventList)
        
        #Find the last entry for each output. This becomes the starting state for each output.
        for Output in self._OutputList:
            #print("Output to search: ", Output)
            for event in reversed(self._EventList):
                #print(event)
                try:
                    DictFound = event[Output]
                    #Note: without the copy command, the next line will link the dictionaries by reference, which we don't want
                    self._EventList[0][Output] = DictFound.copy()  
                    self._EventList[0][Output]['type'] = 'calc'
                    #print(DictFound)
                    break
                except KeyError:
                    pass
                    #print("not found")
        
        i = 0
        for event in self._EventList:
            if i > 0:
                for Output in self._OutputList:
                    #print("Event: ", event)
                    #print("Output: ", Output)
                    try:
                        if event[Output]['type'] == 'calc':
                            #Event found, but it is a calculated event. Update it from the previous event.
                            #print("Output type calc, copying previous")
                            event[Output] = self._EventList[i-1][Output].copy()
                            event[Output]['type'] = 'calc'
                    except KeyError as e:
                        #e is 'type' if the event exsists but does not have a 'type' key.
                        #e is equal to Output if the output does not exsist.
                        if str(e) != "type":
                            #Event not found. Add a calculated event to make state determination easier.
                            #print("Output not present, copying previous")
                            event[Output] = self._EventList[i-1][Output].copy()
                            event[Output]['type'] = 'calc'
            i = i+1
    
        #print("Final Event List:")
        #print(self._EventList)
        
    def GetCurrentState(self, TheTime):
        if isinstance(TheTime, time.struct_time):
            #We are given a time in time_struct format. Convert to a time object.
            CurrentTime = time_obj(TheTime.tm_hour, TheTime.tm_min)
        elif not isinstance(TheTime, time_obj):
            #We are not given either a time or time_struct object.
            raise TypeError('Time must be a time or time_struct object')
        else:
            CurrentTime = TheTime
            
        i = 0
        for event in self._EventList:
            if event['time'] > CurrentTime:     #TODO: What about equality instead of GT/LT?
                return self._EventList[i-1]
            else:
                i = i+1
                
        #We got all the way through the list without finding an event. Return the last event in the list.
        return self._EventList[i-1] 
        
        