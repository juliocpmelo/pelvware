import sys
import glob
import time
import os
from threading import Thread
from pathlib import Path

from PelvwareSerial import PelvwareSerialHandler, PelvwareSerialManager

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QTimer, QObject, QEvent, QRect
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QDialog, QInputDialog, QWidget, QLabel, QListView, QPushButton, QLineEdit, QFormLayout, QVBoxLayout

ser = None
listWifi = None
labelConected = None
buttonConect = None
conected = False
past_result = None
checkSerialTimer = QTimer()
ip_HOST = None




def sendData(data):
    global ser
    #data += "\r\n"
    print("Data: " + data)
    ser.flushInput()
    ser.write(data.encode())


def readData():
    # Definir aqui um tempo de TTL
    global ser
    s1 = ser.readline()
    s1 = s1[:-2]

    return s1.decode("utf-8") 


def Sync(value):
    #####################################################
    # Syncronization with Wemos Serial and Get Wifi List
    #####################################################

    ##############################
    # DEBUG
    #print "Combobox Changed: "
    #print str( value.__str__() )
    global conected
    global ser

    print("Started Sync")
    print(str(value.__str__()))

    if not conected:
        namePort = str(value.__str__())
        print(namePort) 
        ser = serial.Serial(namePort, 115200, timeout=20)
        response = readData()
        
        print("response from board: {} ".format(response))

        if response == "StartConfiguration":
            sendData("ConfigurationStarted")
            time.sleep(5)
            print ("ENVIANDO SERIAL SYNC")
            sendData("SerialSync")

            dataRead = readData()

            ########## DEBUG ###########
            #print len(dataRead)
            #print len("SyncOK")
            print ("OSHE")
            print (dataRead)
            if dataRead == "SyncOK":
                print ("Synchronized")
                # Libera a lista de Wifis e Popula
                UpdateSSIDS()

            else:
                print ("Sync Error")
                # Limpa Lista e Desativa
                model = QStandardItemModel()
                listWifi.setModel(model)
                listWifi.setEnabled(False)
        else: 
            print ("Sync Error")
            # Limpa Lista e Desativa
            model = QStandardItemModel()
            listWifi.setModel(model)
            listWifi.setEnabled(False)


def UpdateSSIDS():

    print ("ENVIANDO GET WIFI LIST UPDATE")
    sendData("GetWifiList")

    lista = readData()

    if lista == "GetWifiListError":
        print (lista)
        listWifi.setEnabled(False)
    else:
        splitedList = lista.split(';')

        model = QStandardItemModel()
        listWifi.setModel(model)
        listWifi.setEnabled(True)

        for i in splitedList:
            item = QStandardItem(i)
            item.setEditable(False)
            model.appendRow(item)


class RefreshComboBox(QObject):
    def eventFilter(self, filteredObj, event):
        if event.type() == QEvent.MouseButtonPress and filteredObj.count() >= 0:
            if not conected:
                global ser
                ser = None
                filteredObj.blockSignals(True)
                filteredObj.clear()
                filteredObj.addItems(serial_ports())
                filteredObj.setCurrentIndex(-1)
                filteredObj.blockSignals(False)
        return QObject.eventFilter(self, filteredObj, event)


class PasswordDialog(QWidget):
    def __init__(self):
        super(PasswordDialog, self).__init__()

        self.initUI()

    def initUI(self):

        self.btn = QPushButton('Dialog', self)
        self.btn.move(20, 20)
        self.btn.clicked.connect(self.showDialog)

        #self.setGeometry(300, 300, 300, 150)
        #self.setFixedSize(300,150)

    def showDialog(self, title, message):

        text, ok = QInputDialog.getText(
            self, title, message, QLineEdit.Normal) # mode=QLineEdit.Password) to not display password.

        if (ok and text):
            return text

def connectionDialog():
    global connected
    waitingConnection = QDialog()
    waitingConnection.setModal(0)
    waitingConnection.setWindowTitle('Connecting')
    waitingConnection.setFixedSize(200,100)
    message = QLabel('Trying to connect...', waitingConnection)
    message.move(20, 40)
    waitingConnection.show()
    # waitingConnection.raise()
    waitingConnection.activateWindow()
    while True:
        a = 1

def window(ip):
    global listWifi
    global labelConected
    global buttonConect
    global checkSerialTimer
    global ip_HOST
    ip_HOST = ip
    print(ip_HOST)
    # app = QApplication(sys.argv)
    win = QDialog()
    # win = QWidget()

    # l1 = QLabel("Select the COM/TTY Port: ")
    # add1 = QComboBox()

    labelConected = QLabel("Not Conected")

    # eventFilter = RefreshComboBox()
    # add1.installEventFilter(eventFilter)
    # add1.currentIndexChanged[str].connect(Sync)

    # checkSerialTimer = QTimer()
    checkSerialTimer.timeout.connect(serial_ports)
    checkSerialTimer.start(1000)

    l2 = QLabel("Select the wireless network SSID:")

    listWifi = QListView()
    listWifi.setGeometry(QRect(10, 50, 231, 221))

    # entries = ['one','two', 'three']

    #for i in entries:
    #    item = QStandardItem(i)
    #    model.appendRow(item)

    fbox = QFormLayout()
    vbox1 = QVBoxLayout()
    vbox2 = QVBoxLayout()
    vbox3 = QVBoxLayout()

    # vbox1.addWidget(add1)
    # fbox.addRow(l1, vbox1)

    vbox2.addWidget(labelConected)
    fbox.addRow(vbox2)

    vbox3.addWidget(listWifi)
    fbox.addRow(vbox3)

    buttonConect = QPushButton("Conectar")
    buttonConect.clicked.connect(requirePassword)
    fbox.addRow(buttonConect)

    win.setLayout(fbox)

    win.setWindowTitle("Pelvware Configuration")
    # win.show()
    # sys.exit(app.exec_())
    win.exec_()


def serialPortLookup():
    serialManager = PelvwareSerialManager()
    return serialManager


"""
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    # return result
    if past_result == None or len(list(set(result) - set(past_result))) <= 0:
        past_result = result
    elif len(list(set(result) - set(past_result))) > 0:
        print("Found the Port")
        print(len(list(set(result) - set(past_result))))
        checkSerialTimer.stop()
        Sync(list(set(result) - set(past_result))[0])
        
"""
        
   
