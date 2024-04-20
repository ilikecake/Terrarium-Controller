'''code.py

This file is a wrapper that does a few setup tasks before executing user code. Move user code to a
file named 'main.py', located in the same directory as code.py

This code does two things:

1. It will check if the file system is read only, and if USB is connected. We assume that if USB is
   connected, that we want the file system set to read only (read only to Circut Python, meaning
   writeable over USB). We also assume that USB is not connected, say because the device is
   connected to a 5V wall wart or something, that we want to enable read/write file system so that
   we can use the wifi workflow. It is not possible to change the read-only-ness of the file system
   from user code, so we do this check here at the start. If we need to update the file system, we
   set a flag in non-volatile memory and hard reset the device. boot.py reads this flag and sets the
   file system accordingly.
   
2. Enables logging to catch errors that crash the user code. I have had a few projects that seem to
   work fine, but will occasionally die and require a power cycle to fix. This is intended to catch
   occasional errors and write them to a file for later inspection. We can only write to the log
   file if the file system is not read-only, hence the implementation of #1 above.

Notes:
 -supervisor.runtime.usb_connected is true when we are connected over USB
 -storage.getmount("/").readonly is true when the file system is read only to circuit python
 -Set microcontroller.nvm[0:1] flag:
    -0xAA to tell the device to make the file system read only (Allow writes over USB)
    -0x55 to tell the device to make the file system read/write. (This disables writing over USB)
'''
import traceback
import microcontroller
import supervisor
import storage
import time
import adafruit_logging as logging
#TODO: Make the log file a setting in settings.toml?
#TODO: Rotate log files so they don't get too big?

fs_obj = storage.getmount("/")

logger = logging.getLogger('error_log')
logger.addHandler(logging.StreamHandler())  #Always write out to REPL
if fs_obj.readonly is False:
    #Write to file if we can
    logger.addHandler(logging.FileHandler('log.txt'))

logger.setLevel(logging.ERROR)

#Not sure if this is needed, but I saw a bootloop when I had no delay here
time.sleep(1)

if supervisor.runtime.usb_connected and (fs_obj.readonly is False):
    #USB is connected and the file system is not readable over USB.
    microcontroller.nvm[0:1] = b"\xaa"
    microcontroller.reset()
elif (supervisor.runtime.usb_connected is False) and fs_obj.readonly:
    #USB not connected, but the file system is readonly to CPy (readable over USB).
    microcontroller.nvm[0:1] = b"\x55"
    microcontroller.reset()
    
#print("USB Status:", supervisor.runtime.usb_connected)
#print("NVM:", microcontroller.nvm[0])
#print("Read Only:", fs_obj.readonly)

try:
    import main
except Exception as e:
    logger.error(traceback.format_exception(e))
    raise e
    