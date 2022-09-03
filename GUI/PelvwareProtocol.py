import enum
#must match PelvwareReceiver.ino and Pelvware.ino
PELVWARE_VERSION = 'Pelvware-1.0.0'
PELVWARE_HEARTBEAT_TIME = 2000 + 1000 #original value is 2 secs (2000), sum another sec for safety

#commands are two bytes followed by \n
class PelvwareCommands:
    STATUS = b'st\n'
    VERSION = b've\n'
    