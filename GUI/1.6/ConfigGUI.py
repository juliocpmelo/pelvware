import sys
import glob
import serial
import serial.tools.list_ports
import time
import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *

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

    return s1


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
        print namePort
        ser = serial.Serial(namePort, 115200, timeout=5)
        response = readData()

        if response == "StartConfiguration":
            sendData("ConfigurationStarted")
            time.sleep(5)
            print "ENVIANDO SERIAL SYNC"
            sendData("SerialSync")

            dataRead = readData()

            ########## DEBUG ###########
            #print len(dataRead)
            #print len("SyncOK")
            print "OSHE"
            print dataRead
            if dataRead == "SyncOK":
                print "Synchronized"
                # Libera a lista de Wifis e Popula
                UpdateSSIDS()

            else:
                print "Sync Error"
                # Limpa Lista e Desativa
                model = QStandardItemModel()
                listWifi.setModel(model)
                listWifi.setEnabled(False)


def UpdateSSIDS():

    print "ENVIANDO GET WIFI LIST UPDATE"
    sendData("GetWifiList")

    lista = readData()

    if lista == "GetWifiListError":
        print lista
        listWifi.setEnabled(False)
    else:
        splitedList = lista.split(';')

        model = QStandardItemModel()
        listWifi.setModel(model)
        listWifi.setEnabled(True)

        for i in splitedList:
            item = QStandardItem(i)
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
            self, title, message, mode=QLineEdit.Normal) # mode=QLineEdit.Password) to not display password.

        if (ok and not (text.isEmpty())):
            return text

def writeIpFile(ip):
    path = os.getcwd()
    access_rights = 0o755
    try:
        if sys.platform == 'linux' or sys.platform == 'linux2':
            os.mkdir(path+'/bin', access_rights)
        elif sys.platform == 'win32':
            os.mkdir(path+'\\bin', access_rights)

    except OSError:
        print("A pasta ja existe")
        createFile(path, ip)
    else:
        createFile(path, ip)

def createFile(path, ip):
    if sys.platform == 'linux' or sys.platform == 'linux2':
        f = open(path+"/bin/.pelvIp.file", "w+")
        f.write(ip)
    elif sys.platform == 'win32':
        f = open(path+"\\bin\\.pelvIp.file", "w+")
        f.write(ip)

def requirePassword():
    ##################################################
    # Require the password of the wireless network
    ##################################################
    global conected
    global listWifi
    global ip_HOST
    # gets the selected indexes in the 'QListView'

    if not conected:
        selected_indexes = listWifi.selectedIndexes()

        if len(selected_indexes) > 0:
            # gets the selected rows
            selected_rows = [item.row() for item in selected_indexes]

            ssid = selected_indexes[0].data().toString()

            janela = PasswordDialog()
            senha = janela.showDialog('Password Required',
                                      'Enter the network password:')

            print "SENHA"
            print senha
            # Verify spaces on the password
            if senha != None:
                #print "SSID: " + ssid + " Senha: " + senha
                connect = ssid + ";" + senha + ";" + ip_HOST
                print(connect)
                print "ENVIANDO SSID + SENHA + IP"
                sendData(str(connect))
                time.sleep(10)
                response = readData()

                if response == "Connected":
                    ip = readData()
                    print response + " IP " + ip
                    conected = True
                    labelConected.setText("Connected: " + ip)
                    writeIpFile(ip)
                    listWifi.setEnabled(False)
                    buttonConect.setEnabled(False)
                else:
                    print "Erro Conexao"
                    print "Error Message: " + response
                    UpdateSSIDS()
                    conected = False
            else:
                print "SSID + SENHA INVALIDO"
                sendData("0")
                response = readData()
                print "QUE FOI ISSO"
                print response

                UpdateSSIDS()
                conected = False

def connectionDialog():
    global connected
    waitingConnection = QDialog()
    waitingConnection.setWindowTitle('Connecting')
    waitingConnection.setFixedSize(200,100)
    waitingConnection.exec_()

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
    checkSerialTimer.start(1)

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

def serial_ports():
    global past_result
    global checkSerialTimer
    global ser

    print (past_result)

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
