from concurrent.futures import thread
import sys
import time
from PelvwareProtocol import PelvwareCommands
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal
from math import floor
from threading import Thread, Condition, Timer
import pyqtgraph as pg
import numpy as np
import socket
import os
import ConfigGUI
import csv
from pathlib import Path
from PelvwareSerial import PelvwareSerialHandler, PelvwareSerialManager
from Util import RepeatTimer
import math




class ApplicationWindow(QtWidgets.QMainWindow, PelvwareSerialHandler):

    data_received_sig = pyqtSignal([float, float, float])
    pelvware_connect_sig = pyqtSignal()
    pelvware_disconnect_sig = pyqtSignal()
    
    #fake data methods
    def fakeDataGenerator(self):
        amplitude = 0.1
        period = 10000 #(ms)
        #x = time.time() * 1000 - self.start_time
        if self.connected == 1:
            x = self.last_x
            y = amplitude * math.sin(2*math.pi/period*x) + amplitude
            self.last_x = self.last_x + 50
            self.data_received_sig.emit(x,y,5)
        
    def fakeConnectionGenerator(self):
        self.pelvware_connect_sig.emit()
        self.fake_data_timer = RepeatTimer(0.01, self.fakeDataGenerator)
        self.fake_data_timer.start()
        

    ## Function that starts the main GUI. It's responsible for calling all the
    ## functions that handle the data processing, hardware interfacing and
    ## graphic plotting.
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Pelvware")

        self.configWindow = None
        self.dialog = None

        self.rate = 0.4
        
        #total msecs that are visible in the online mode
        self.default_view_secs = 10

        ## A Timer object, we run the connection health function through it.
        #self.timer1 = QtCore.QTimer()

        #self.timer1.timeout.connect(self.connectionHealth)

        ## Declaration of the threads used in receiving, plotting and processing the data.
        #self.rcvThread = Thread(target=self.udpThread)
        #self.processingThread = Thread(target=self.processDataThread)
        #self.plotThread = Thread(target=self.pltThread)

        #self.rcvThread.daemon = True
        #self.processingThread.daemon = True
        #self.plotThread.daemon = True

        # Threads Controllers and Condiotions.
        self.connected = 0
        self.controleTeste = False ## Controller of the pause function. 0 = running, and 1 = paused

        self.hasData = Condition()
        self.hasProcData = Condition()
        self.hasNew = False

        self.startTime = time.time()

        # Which protocol we're currently running.
        self.currentProtocol = ''

        # File to be Plotted Statically.
        self.fileName = ''

        # Info on the current Mode, if it's the RT we also have the acquisition state.
        # readingMode (true = RT, false = FTP) always starts with false.
        # rtState (true = Active, false = Inactive) always starts inactive.
        # viewingMode (true = pages of 45s, false = standard with p2 as scrolling)
        self.readingMode = False
        self.rtState = False
        self.viewingMode = False

        # Network Configuration of Host and Port.
        self.HOST = ''
        self.PORT = 5000
        self.udp = 0

        # Data to be plotted or processed.
        self.dataToBeProcessed = []
        self.x = []
        self.y = []
        self.dummy_value = 0
        self.time_dummy_value = 0.0

        # Variables used to mark the range of the x-axis.
        self.endX = 45
        self.startX = 0
        self.countX = 0

        self.statsCounter = 0
        self.statistics = []

        # Creation of the menu File
        self.file_menu = QtWidgets.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.selectFile)
        self.file_menu.addAction('&Save')
        self.file_menu.addAction('&Clear Data', self.clearData)
        self.file_menu.addAction('&Close', self.fileQuit)

        self.menuBar().addMenu(self.file_menu)

        # Creation of the main Widget and of the organizational layouts.
        self.centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.centralWidget)

        ## Configuring the layout of the main gui.
        self.hBoxLayout1 = QtWidgets.QHBoxLayout()
        self.vBoxLayout = QtWidgets.QVBoxLayout()
        self.vBoxLayout2 = QtWidgets.QVBoxLayout()

        self.hBoxLayout1.addLayout(self.vBoxLayout)
        self.hBoxLayout1.addLayout(self.vBoxLayout2)
        self.centralWidget.setLayout(self.hBoxLayout1)
        self.setGeometry(300, 300, 300, 300)

        ## Configuring the plotting object.
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'r')
        pg.setConfigOption('leftButtonPan', False)

        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel()
        self.label3 = QtWidgets.QLabel()
        self.connectionStatusLabel = QtWidgets.QLabel()
        self.label5 = QtWidgets.QLabel()
        self.label6 = QtWidgets.QLabel()

        self.label3.setText('Current Status')
        

        self.label5.setText('Current Protocol')
        self.label6.setText(self.currentProtocol)
        self.label6.setStyleSheet('color: blue')

        self.btn = QtWidgets.QPushButton('Default')
        self.testModeBtn = QtWidgets.QPushButton('Toogle Test Mode')
        self.holdPlotButton = QtWidgets.QPushButton('Hold Plot')
        self.btn4 = QtWidgets.QPushButton('Change Modes')
        self.btn5 = None
        self.btn6 = QtWidgets.QPushButton('Change Viewing Mode')
        self.btn7 = None
        self.btn8 = None

        self.btn.clicked.connect(self.buttonDefault)
        self.testModeBtn.clicked.connect(self.toogleTestMode)
        self.holdPlotButton.clicked.connect(self.buttonPause)
        self.btn4.clicked.connect(self.buttonChange)
        self.btn6.clicked.connect(self.fileViewingMode)

        self.mainPlot = pg.PlotWidget()  # Main plot
        self.mainPlot.setLabel(axis='bottom', text='Time', units='sec')
        self.mainPlot.setLabel(axis='left', text='Voltage', units='volt')
        self.mainPlot.showGrid(x=False, y=True)
        self.vBoxLayout2.addWidget(self.mainPlot, stretch=6)
        
        
        self.scrollingPlot = pg.PlotWidget(enableMenu=False, enableMouse=False,lockAspect=False)  # Scrolling Plot
        self.scrollingPlot.setLabel(axis='bottom', text='Time', units='sec')
        self.scrollingPlot.setLabel(axis='left', text='Voltage', units='volt')
        self.scrollingPlot.showGrid(x=False, y=True)
        self.scrollingPlot.setMouseEnabled(x=False, y=False)
        self.vBoxLayout2.addWidget(self.scrollingPlot, stretch=1)
        self.scrollingPlot.hide()
        
        self.scrollingPlotSelectRect = pg.LinearRegionItem(values=(-self.default_view_secs/2, self.default_view_secs/2))
        self.scrollingPlotSelectRect.sigRegionChanged.connect(self.scrollingPlotSelctRectMoved)
        self.scrollingPlot.addItem(self.scrollingPlotSelectRect)
        
        
        self.clearData()
        self.setConnectionStatus(False)

        # Element for the threshold used in the continuous protocol.
        self.threshold = None

        ## Adding elements to main GUI.
        self.vBoxLayout.addWidget(self.label3)
        self.vBoxLayout.addWidget(self.connectionStatusLabel)
        self.vBoxLayout.addWidget(self.btn4)
        self.vBoxLayout.addWidget(self.testModeBtn)
        self.vBoxLayout.addWidget(self.holdPlotButton)
        self.vBoxLayout.addWidget(self.btn)
        self.vBoxLayout.addWidget(self.btn6)
        self.vBoxLayout.addWidget(self.label5)
        self.vBoxLayout.addWidget(self.label6)
        self.vBoxLayout.addWidget(self.label1)
        self.vBoxLayout.addWidget(self.label2)
        self.vBoxLayout.addStretch(1)
        self.setGeometry(300, 300, 1200, 800)


        self.btn.setEnabled(False)
        self.holdPlotButton.setEnabled(False)
        self.testModeBtn.setEnabled(False)
        
        
        self.data_received_sig.connect(self.onDataReceived)
        self.pelvware_connect_sig.connect(self.onPelvwareConnect)
        self.pelvware_disconnect_sig.connect(self.onPelvwareDisconnect)
        
        self.plotPaused = False
        
        self.serialManager = PelvwareSerialManager()
        self.serialManager.addSerialHandler(self)
        
        self.showingScrollingPlot = False
      
      
    def scrollingPlotSelctRectMoved(self, rect):
        reg = rect.getRegion()
        self.updateMainPlotView(reg)
        #print("vals {}".format(reg))
        

    def setCommandOptions(self, cmdOptions):
        self.localTestMode = cmdOptions.test
        #stops serial serial manager and starts local test mode
        #in this mode we can debug the plot by using local generated data
        if self.localTestMode :
            self.serialManager.stopAllThreads()
            self.degree = 0
            self.start_time = time.time() * 1000
            self.last_x = 0
            self.fake_connection = Timer(1, self.fakeConnectionGenerator, [])
            self.fake_connection.start()
            
            

    def clearData(self):
        self.x = [0]
        self.y = [0]
        self.endX = self.default_view_secs
        self.startX = 0.0
        # self.x.append(0)
        # self.y.append(0.0)
        self.mainPlot.clear()
        # self.p2.clear()

        # self.p1.setDownsampling(mode='peak')
        # self.p2.setDownsampling(mode='peak')

        # self.p1.setClipToView(True)
        # self.p2.setClipToView(True)

        self.mainPlot.setXRange(self.startX, self.endX, padding=0)
        self.mainPlot.setYRange(0, self.rate, padding=0)

        self.curve1 = self.mainPlot.plot(x=self.x, y=self.y, pen='r')
        self.curve2 = self.scrollingPlot.plot(x=self.x, y=self.y, pen='r')

        #self.label1.setText('Status da Conexao')

        if self.currentProtocol == "Continuous":
            self.threshold = pg.InfiniteLine(pos=500, angle=0, movable=True, pen='b')
            self.mainPlot.addItem(self.threshold, ignoreBounds=True)  
        
        

    def toogleTestMode(self):
        if self.serialManager is not None:
            self.serialManager.sendCommand(PelvwareCommands.TOOGLE_TEST_MODE)
                
        
    def dialogButton(self):
        self.config()
        self.dialog.close()

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        #self.timer1.stop()
        self.fileQuit()
        if self.serialManager is not None:
            self.serialManager.stopAllThreads()
        if self.localTestMode :
            self.fake_data_timer.cancel()
            self.fake_data_timer.join()

    ## Separate the data received, add into a list and then calculate the real
    ## value.
    def separateData(self, file):
        for line in file:
            a, b = line.split(';')
            self.x.append(a)
            self.y.append(b)

        self.x = list(map(float, self.x))
        self.y = list(map(float, self.y))


        ## Calculate the real value, taking into account the amplification from
        ## the hardware.
        # self.y = map(lambda a: (((a * (3.2 / 1023)) / 10350) * 1000), self.y)

    def selectFile(self):
        self.fileName = QtWidgets.QFileDialog.getOpenFileName()
        self.plotFile()

    ## Function to make a static plot out of a file.
    def plotFile(self):
        # if self.fileName.contains(".csv"):
        #     file = csv.reader(self.fileName, delimiter=';')
        # else:
        file = open(self.fileName, 'r')

        self.mainPlot.clear()
        self.scrollingPlot.clear()

        self.mainPlot.setDownsampling(mode='peak')
        self.scrollingPlot.setDownsampling(mode='peak')

        self.mainPlot.setClipToView(False)
        self.scrollingPlot.setClipToView(False)

        self.x = []
        self.y = []
        self.separateData(file)

        print(self.x[-1])
        print(self.y[-1])
        self.mainPlot.setXRange(0, self.x[-1] * 0.1, padding=0)

        self.curve1 = self.mainPlot.plot(x=self.x, y=self.y, pen='r')
        self.curve2 = self.scrollingPlot.plot(x=self.x, y=self.y, pen='r')
        self.zoomLinearRegion = pg.LinearRegionItem([0, (self.x[-1] * 0.1)])
        self.zoomLinearRegion.setZValue(-10)

        self.scrollingPlot.addItem(self.zoomLinearRegion)

        self.mainPlot.setYRange(0, self.rate, padding=0)

        self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
        self.mainPlot.sigXRangeChanged.connect(self.updateRegion)

        self.btn.setDisabled(False)
        self.updatePlot()

    def plotPagedFile(self):
        try:
            self.hideScrollingPlot()
        except RuntimeError:
            print("ScrollingPlot Doesn't exist")
        file = open(self.fileName, 'r')

        self.mainPlot.clear()
        self.mainPlot.setDownsampling(mode='peak')
        self.mainPlot.setClipToView(True)

        self.x = []
        self.y = []
        self.separateData(file)

        self.startX = 0.0
        self.endX = 45.0

        self.mainPlot.setXRange(self.startX, self.endX, padding=0)
        self.mainPlot.setYRange(0, self.rate, padding=0)

        self.curve1 = self.mainPlot.plot(x=self.x, y=self.y, pen='r')

    def updatePlots(self):
        while True:
            time.sleep(0.1)
            self.time_dummy_value += 0.001
            self.dummy_value += 1
            self.y.append(self.time_dummy_value)
            self.x.append(self.dummy_value)

            self.mainPlot.setXRange(0, self.x[-1] * 0.1, padding=0)
            self.mainPlot.setYRange(0, self.rate, padding=0) ## Original should be 0.4 instead of 1024.

            self.curve1.setData(self.x, self.y)
            self.curve2.setData(self.x, self.y)

            # self.zoomLinearRegion.setRegion(
            #     [self.x[-1] - self.x[-1] * 0.1, self.x[-1]])

            self.updatePlot()
            # time.sleep(5)

    def updatePlot(self):
        self.mainPlot.setXRange(*self.zoomLinearRegion.getRegion(), padding=0)

    def updateMainPlotView(self, region=None):
        #window will follow if the current sample is greater than half of visible window
        if self.x[-1] >= self.default_view_secs/2 and not self.plotPaused:
            self.startX = self.x[-1] - self.default_view_secs/2
            self.endX = self.x[-1] + self.default_view_secs/2
            
            self.countX = self.countX + 1
            if self.countX == 1 and self.currentProtocol == 'Evaluative':
                self.protLinearRegion = pg.LinearRegionItem([self.startX + 25.0, self.startX + 35.0])
                self.mainPlot.addItem(self.protLinearRegion)
            if self.countX == 2 and self.currentProtocol == 'Evaluative':
                self.protLinearRegion = pg.LinearRegionItem([self.startX + 25.0, self.startX + 35.0])
                self.mainPlot.addItem(self.protLinearRegion)
            elif self.countX > 2:
                self.countX = 0
                self.statsCounter += 3
            self.mainPlot.setXRange(self.startX, self.endX, padding=0)
        elif region is not None: #when plot is paused we can still scroll using the scrolling area
            self.startX = region[0]
            self.endX = region[1]
            self.mainPlot.setXRange(self.startX, self.endX, padding=0)
            
        
        
        # if self.currentProtocol == "Continuous":
        #     self.threshold = pg.InfiniteLine(pos=0.5, angle=0, movable=True)
        #     self.p1.addItem(self.threshold)
        #     print("OI")

    def updateRegion(self):
        if self.controleTeste:
            self.zoomLinearRegion.setRegion(self.mainPlot.getViewBox().viewRange()[0])

    def writeFile(self, text):
        file = open('teste.log', 'a')
        file.write(text)
        file.write('\n')

    def hideScrollingPlot(self):
        self.scrollingPlot.hide()

    def showScrollingPlot(self):
        
        self.scrollingPlot.show()
        self.scrollingPlotSelectRect.setRegion((self.x[-1] - self.default_view_secs/2,
                                                self.x[-1] + self.default_view_secs/2))
        

        if self.readingMode:
            self.scrollingPlot.setDownsampling(mode='peak')

            self.scrollingPlot.setClipToView(True)

            self.curve2 = self.scrollingPlot.plot(x=self.x, y=self.y, pen='r')
            # self.zoomLinearRegion = pg.LinearRegionItem([0, (self.x[-1] * 0.1)])
            self.zoomLinearRegion = pg.LinearRegionItem([0, 2])
            self.zoomLinearRegion.setZValue(-10)

            self.scrollingPlot.addItem(self.zoomLinearRegion)

            self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
            self.mainPlot.sigXRangeChanged.connect(self.updateRegion)
            self.updatePlot()


    def buttonDefault(self):
        if not self.readingMode:
            region = self.zoomLinearRegion.getRegion()
            new_region = [floor(region[0]), floor(region[0]) + (self.x[-1] * 0.1)]
            self.zoomLinearRegion.setRegion(new_region)

        self.updatePlot()
        self.mainPlot.setYRange(0, self.rate, padding=0) # Original should be 0.4 instead of 1024


    def buttonPause(self):
        self.controleTeste = not self.controleTeste
        self.plotPaused = not self.plotPaused
        if not self.controleTeste:
            self.btn.setEnabled(False)
            self.hideScrollingPlot()
        else:
            self.btn.setDisabled(False)
            self.showScrollingPlot()


    def buttonChange(self):
        if not self.readingMode:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print ("ip {} port {}".format(self.pelvIP, self.pelvPORT))
            sock.sendto(b'changeMode', (self.pelvIP, self.pelvPORT))
            sock.close()
            self.readingMode = not self.readingMode
            # self.rtState = not self.rtState
            self.btn5 = QtWidgets.QPushButton('Start Data Acquisition')
            self.btn5.clicked.connect(self.buttonPauseRT)
            #self.testModeBtn.setDisabled(False)
            self.vBoxLayout.addWidget(self.btn5)
            self.hideScrollingPlot()
            #self.connectionStatusLabel.setText("RT")
            #self.connectionStatusLabel.setStyleSheet('color : green')

        else:
            self.btn5.deleteLater()
            self.connected = 1
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(b'changeMode', (self.pelvIP, self.pelvPORT))
            sock.close()
            self.protocolWindow()
            #self.testModeBtn.setEnabled(False)
            self.readingMode = not self.readingMode
            self.vBoxLayout.removeWidget(self.btn5)
            #self.connectionStatusLabel.setText("FTP")
            #self.connectionStatusLabel.setStyleSheet('color : blue')
            try:
                self.hideScrollingPlot()
            except:
                print("Grafico inexistente")
            self.showScrollingPlot()



    def buttonPauseRT(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.rtState:
            sock.sendto(b'pauseRT', (self.pelvIP, self.pelvPORT))
            self.btn5.setText('Start Data Acquisition')
            self.showScrollingPlot()

        else:
            sock.sendto(b'startRT', (self.pelvIP, self.pelvPORT))
            self.btn5.setText('Pause Data Acquisition')
            try:
                self.hideScrollingPlot()
            except:
                print('Grafico inexistente')


        self.rtState = not self.rtState


    def buttonConnect(self):
        if self.connected == 0:
            self.connected = 1
            self.holdPlotButton.setDisabled(False)
            #self.testModeBtn.setEnabled(True)
            # self.controleTeste = 0
            self.x = [0]
            self.y = [0]
            self.endX = 45.0
            self.startX = 0.0
            # self.x.append(0)
            # self.y.append(0.0)
            self.mainPlot.clear()
            # self.p2.clear()

            self.mainPlot.setDownsampling(mode='peak')
            # self.p2.setDownsampling(mode='peak')

            self.mainPlot.setClipToView(True)
            # self.p2.setClipToView(True)

            self.mainPlot.setXRange(self.startX, self.endX, padding=0)

            self.curve1 = self.mainPlot.plot(x=self.x, y=self.y, pen='r')

            self.label1.setText('Status da Conexao')

            if self.currentProtocol == "Continuous":
                self.threshold = pg.InfiniteLine(pos=500, angle=0, movable=True, pen='b')
                self.mainPlot.addItem(self.threshold, ignoreBounds=True)

        else:
            # self.controleTeste = not self.controleTeste
            # try:
            #     self.buttonPause()
            # except:
            #     print("Grafico despausado")
            self.btn.setEnabled(False)
            self.holdPlotButton.setEnabled(False)
            self.connected = 0

    @QtCore.pyqtSlot(float, float, float)
    def onDataReceived(self, time, volts, time_between_messages):
        if len(self.x) == 0 or time > self.x[-1] :
            #print('appending {} {} '.format(x_val, y_val))
            self.x.append(time/1000) #time is received in millisecs
            self.y.append(volts) #y val is received in volts

            #add to main plot            
            self.curve1.setData(self.x, self.y)
            #add to scrolling plot
            self.curve2.setData(self.x, self.y)
            
            self.updateMainPlotView()
    
    def setConnectionStatus(self, connected):
        if connected :
            self.connected = 1
            self.testModeBtn.setEnabled(True)
            self.holdPlotButton.setEnabled(True)
            self.connectionStatusLabel.setText('Connected')
            self.connectionStatusLabel.setStyleSheet('color : green')
        else:
            self.connected = 0
            self.holdPlotButton.setEnabled(False)
            self.testModeBtn.setEnabled(False)
            self.connectionStatusLabel.setText('Disconnected')
            self.connectionStatusLabel.setStyleSheet('color : red')
            
            
    
    @QtCore.pyqtSlot()
    def onPelvwareConnect(self):
        #print("Pelvware connected")
        self.setConnectionStatus(True)
        #self.clearData()
        
    @QtCore.pyqtSlot()
    def onPelvwareDisconnect(self):
        self.setConnectionStatus(False)
        #self.clearData()
        
    #override from PelvwareSerialHandler
    def onData(self, data):
        # print(self.dataToBeProcessed)
        if data.find('OK') == -1 :
            a, b, c = data.split(' ')
            try:
                time = float(b) #timestamp in millis
                volts = float(a) #read voltage in volts
                diff_time = float(c) # time difference between messages, the bigger the worst
                self.data_received_sig.emit(time, volts, diff_time)
            except:
                print("converstion error: {}".format(data))
        else :
            print ('got ' + data)
        
    def onDisconnect(self):
        self.pelvware_disconnect_sig.emit()
        
    def onConnect(self, port):
        print ('pelvware connectedt to port ' + str(port))
        self.pelvware_connect_sig.emit()
      
    def connectionHealth(self):
        if (time.time()-self.startTime) < 0.02:
            self.label2.setText('Muito Boa')
            self.label2.setStyleSheet('color: green')
        elif (time.time()-self.startTime) < 0.1:
            self.label2.setText('Boa')
            self.label2.setStyleSheet('color: green')
        elif (time.time()-self.startTime) < 0.5:
            self.label2.setText('Ruim')
            self.label2.setStyleSheet('color: yellow')
        elif (time.time()-self.startTime) < 1:
            self.label2.setText('Muito Ruim')
            self.label2.setStyleSheet('color: orange')
        else:
            self.label2.setText('Desconectado')
            self.label2.setStyleSheet('color: red')


    def config(self):
        self.configWindow = ConfigGUI.window(self.HOST)
        self.readPelvIP()

    def protocolWindow(self):
        if self.connected == 0:
            # app = QApplication(sys.argv)
            win = QtWidgets.QDialog()
            win.setGeometry(400, 300, 200, 100)
            layout = QtWidgets.QVBoxLayout()

            self.b1 = QtWidgets.QRadioButton("Continuous")
            self.b1.setChecked(True)
            layout.addWidget(self.b1)

            self.b2 = QtWidgets.QRadioButton("Evaluative")

            btn = QtWidgets.QPushButton('Ok')
            btn.clicked.connect(self.selectedProtocol)
            btn.clicked.connect(self.buttonConnect)
            btn.clicked.connect(win.close)

            layout.addWidget(self.b2)
            layout.addWidget(btn)
            win.setLayout(layout)
            win.setWindowTitle("Choose Your Protocol")
            win.exec_()
        else:
            self.buttonConnect()
            self.saveSession()

    def selectedProtocol(self):
        if self.b1.isChecked() == True:
            self.currentProtocol = "Continuous"
        elif self.b2.isChecked() == True:
            self.currentProtocol = "Evaluative"
        self.label6.setText(self.currentProtocol)

    def saveSession(self):
        fileName = QtWidgets.QFileDialog.getSaveFileName(parent=self, caption="Save File",
                                       filter="CSV Files (*.csv)")
        if fileName[0] : #arquivo selecionado / nome digitado
            with open(fileName[0], 'w') as csvfile:
                filewriter = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                print("Self.x Length:", len(self.x))
                print()
                i = 0
                while i < len(self.x):
                    filewriter.writerow([self.x[i]] + [self.y[i]])
                    i = i+1

    def testFunc(self):
        if self.currentProtocol == "Continuous":
            average = np.mean(self.y)
            median = np.median(self.y)
            std = np.std(self.y)
            max = np.amax(self.y)

            if len(self.statistics) != 0:
                self.statistics[0] = average
                self.statistics[1] = median
                self.statistics[2] = std
                self.statistics[2] = max
            else:
                self.statistics.append(average)
                self.statistics.append(median)
                self.statistics.append(std)
                self.statistics.append(max)
            print("Stats: ", self.statistics)

        elif self.currentProtocol == "Evaluative":
            if self.countX == 0:
                try:
                    average = np.mean(self.y[self.x.index(int(self.startX)):self.x.index(int(self.endX))])
                    median = np.median(self.y[self.x.index(int(self.startX)):self.x.index(int(self.endX))])
                    std = np.std(self.y[self.x.index(int(self.startX)):self.x.index(int(self.endX))])
                    max = np.amax(self.y[self.x.index(int(self.startX)):self.x.index(int(self.endX))])
                except ValueError as e:
                    average = np.mean(self.y)
                    median = np.median(self.y)
                    std = np.std(self.y)
                    max = np.amax(self.y)

                stats_list = [average, median, std, max]
            elif self.countX >= 1:
                x = int(self.protLinearRegion.getRegion()[0])
                y = int(self.protLinearRegion.getRegion()[1])
                try:
                    average = np.mean(self.y[self.x.index(x):self.x.index(y)])
                    median = np.median(self.y[self.x.index(x):self.x.index(y)])
                    std = np.std(self.y[self.x.index(x):self.x.index(y)])
                    max = np.amax(self.y[self.x.index(x):self.x.index(y)])
                    stats_list = [average, median, std, max]
                except ValueError as e:
                    stats_list = [0, 0, 0, 0]
                    print("Ainda nao chegamos na zona")
                    print("X", x)
                    print("Y", y)


            try:
                self.statistics[self.countX+self.statsCounter] = stats_list
            except IndexError as e:
                self.statistics.append(stats_list)

            print(self.statistics)

    def nextPage(self):
        self.startX = self.endX
        self.endX = self.startX + 45.0
        self.mainPlot.setXRange(self.startX, self.endX, padding=0)

    def previousPage(self):
        self.endX = self.startX
        self.startX = self.endX - 45.0
        self.mainPlot.setXRange(self.startX, self.endX, padding=0)

    def fileViewingMode(self):
        if self.viewingMode == True:
            self.viewingMode = not self.viewingMode
            try:
                self.btn6.deleteLater()
                self.btn7.deleteLater()

                self.vBoxLayout.removeWidget(self.btn6)
                self.vBoxLayout.removeWidget(self.btn7)
            except:
                print("Buttons don't exist")
            self.showScrollingPlot()
            self.plotFile()
        elif self.viewingMode == False:
            self.viewingMode = not self.viewingMode
            if not self.rtState:
                self.btn6 = QtWidgets.QPushButton('<< Previous Page')
                self.btn7 = QtWidgets.QPushButton('>> Next Page')

                self.btn6.clicked.connect(self.previousPage)
                self.btn7.clicked.connect(self.nextPage)

                self.vBoxLayout.addWidget(self.btn6)
                self.vBoxLayout.addWidget(self.btn7)

            self.plotPagedFile()

import argparse

def parseCommandArgs():
    parser = argparse.ArgumentParser(description='Pelvware Command Line')
    parser.add_argument('--test', action='store_true')
    return parser.parse_args()

def main():
    commandOptions = parseCommandArgs()
    qApp = QtWidgets.QApplication(sys.argv)

    applicationWindow = ApplicationWindow()
    applicationWindow.setCommandOptions(commandOptions)
    applicationWindow.show()

    sys.exit(qApp.exec_())

if __name__=='__main__':
    main()


