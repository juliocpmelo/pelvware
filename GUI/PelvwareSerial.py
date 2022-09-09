import time
from threading import Thread, Lock, Timer
from pathlib import Path

from PelvwareProtocol import PelvwareCommands, PELVWARE_VERSION, PELVWARE_HEARTBEAT_TIME

import serial
import serial.tools.list_ports
import enum


class CommunicationEvents(enum.Enum):
    CONNECTED = 1
    DISCONNECTED = 2
    DATA = 3
    
class PelvwareSerialHandler:
    def onData(self,data):
        pass
    def onDisconnect(self):
        pass
    def onConnect(self,port):
        pass



    
            
class PelvwareSerialManager:
    
    def __init__(self):
        self.serial_threads = []
        self.connected = False
        self.pelvware_port = ''
        self.handlers = []
        
        self.command_queue_lock = Lock()
        self.command_queue = []
        
        self.terminate = False
        
        #creates one thread for each serial port and poll for pelvware in each
        #the polling is done by sending the VERSION command and checking the result
        self.serial_timer = Timer(2, self.findPelvware, [])
        self.serial_timer.start()
        print ('starting threads')

    def findPelvware(self):
        #tests all serial ports for a pelvware
        #if any is found, starts the dataHandler thread on it
        list = serial.tools.list_ports.comports()
        for p in list:
            print ("Checking for pelvware at port " + p.device)
            with serial.Serial(port=p.device, baudrate=115200, timeout=1) as serial_comm:
                serial_comm.write(PelvwareCommands.VERSION)
                data = serial_comm.readline()
                data_str = data.decode(errors='ignore')
                data_str = data_str.rstrip()
                #print('got {}'.format(data_str))
                if data_str.startswith('d') and data_str[2:] == PELVWARE_VERSION:
                    self.pelvwareFound(p.device)
                    self.dataHandler(serial_comm)
                    break
            
        #restarts timer if lost connection, except if its going to terminate
        if not self.terminate:
            self.serial_timer = Timer(2, self.findPelvware, [])
            self.serial_timer.start()

    def stopAllThreads(self):
        #every thread should run for just 5 secs, thus this method should not block
        #more much more than this
        print ('stooping threads')
        self.serial_timer.cancel()
        self.terminate = True
        self.serial_timer.join()
            
    def isConnected(self):
        return self.serial_port != ''
    
    def addSerialHandler(self,handler):
        self.handlers.append(handler)
        
    #sends a command, data callbacks should receive the result once its fetched
    def pelvwareFound(self,serial_port):
        self.pelvware_port = serial_port
            
    def notifyHandlers(self, event, data = None):
        if event == CommunicationEvents.CONNECTED:
            for h in self.handlers:
                h.onConnect(data)
        if event == CommunicationEvents.DISCONNECTED:
            for h in self.handlers:
                h.onDisconnect()
        if event == CommunicationEvents.DATA:
            for h in self.handlers:
                h.onData(data)

    #command queue, commands will be queueed until executed
    def commandPending(self):
        with self.command_queue_lock:
            return len(self.command_queue) > 0
    def sendCommand(self, command):
        with self.command_queue_lock:
            self.command_queue.append(command)
    def getNexCommand(self):
        with self.command_queue_lock:
            return self.command_queue.pop()
        
    #data thread 
    def dataHandler(self, serial_comm):
        current_command = None
        connected = False
        timeLastData = time.time()*1000
        while True: #loops forever except when there is an error on write or read
            #sends commands if there is any
            current_time = time.time()*1000
            try:
                #send commands
                if self.commandPending() and current_command == None:
                    current_command = self.getNexCommand()
                    serial_comm.write(current_command)
                #aways read data
                data = serial_comm.readline()
            except Exception as e: #any error on writing/reading
                self.notifyHandlers(CommunicationEvents.DISCONNECTED)
                break
            
            data_str = data.decode(errors='ignore')
            data_str = data_str.rstrip()
            #print ('got {}'.format(data_str))
            if len(data_str) > 0 :
                if data_str.startswith('a'): #answer to command sent
                    current_command = None
                elif data_str.startswith('d'):
                    #data comes formatted as "d float unsigned long" 
                    #thus we remove d from protocol and pass on data
                    if not data_str.find('FAIL') >= 0 and not data_str.find('OK') >= 0 : #FAIL/OK command response
                        timeLastData = current_time
                        if not connected :
                            self.notifyHandlers(CommunicationEvents.CONNECTED)
                            connected = True
                        self.notifyHandlers(CommunicationEvents.DATA, data_str[2:])
                    else: #answer to command go to next command
                        current_command = None
            if current_time - timeLastData > PELVWARE_HEARTBEAT_TIME and connected: #disconnected due to latency or other communication problems
                self.notifyHandlers(CommunicationEvents.DISCONNECTED)
                connected = False
            if self.terminate :
                break
                
                    
        

    #looks for pelvware at a given port
    #this thread sends the version command and waits for response up to 5 times
                    
        
