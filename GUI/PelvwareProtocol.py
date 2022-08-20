import enum
#must match PelvwareReceiver.ino and Pelvware.ino
PELVWARE_VERSION = 'Pelvware-1.0.0'

#commands are two bytes followed by \n
class PelvwareCommands:
    STATUS = b'st\n'
    VERSION = b've\n'
    