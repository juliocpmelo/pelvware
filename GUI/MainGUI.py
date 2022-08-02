import sys
import time
from PyQt4 import QtGui, QtCore
from math import floor
from threading import Thread, Condition
import pyqtgraph as pg
import numpy as np
import socket
import os
import select
import ConfigGUI
import csv

class ApplicationWindow(QtGui.QMainWindow):

    ## Function that starts the main GUI. It's responsible for calling all the
    ## functions that handle the data processing, hardware interfacing and
    ## graphic plotting.
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Pelvware")

        self.configWindow = None
        self.dialog = None

        self.rate = 1024

        ## A Timer object, we run the connection health function through it.
        self.timer1 = QtCore.QTimer()

        self.timer1.timeout.connect(self.connectionHealth)

        ## Declaration of the threads used in receiving, plotting and processing the data.
        self.rcvThread = Thread(target=self.udpThread)
        self.processingThread = Thread(target=self.processDataThread)
        self.plotThread = Thread(target=self.pltThread)

        self.rcvThread.daemon = True
        self.processingThread.daemon = True
        self.plotThread.daemon = True

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
        self.readingMode = False;
        self.rtState = False
        self.viewingMode = False

        # Network Configuration of Host and Port.
        self.HOST = ''
        self.PORT = 5000
        self.udp = 0
        self.discoverIp()
        self.orig = (self.HOST, self.PORT)

        # The following IP and port are from the Pelvware, in  the future we should keep this data in a file containing the info on
        # many devices
        self.pelvIP = ''
        self.pelvPORT = 7500

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
        self.file_menu = QtGui.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.selectFile)
        self.file_menu.addAction('&Save')
        self.file_menu.addAction('&Configure Pelvware', self.config)
        self.file_menu.addAction('&Close', self.fileQuit)

        self.menuBar().addMenu(self.file_menu)

        # Creation of the main Widget and of the organizational layouts.
        self.centralWidget = QtGui.QWidget()
        self.setCentralWidget(self.centralWidget)

        ## Configuring the layout of the main gui.
        self.hBoxLayout1 = QtGui.QHBoxLayout()
        self.vBoxLayout = QtGui.QVBoxLayout()
        self.vBoxLayout2 = QtGui.QVBoxLayout()

        self.hBoxLayout1.addLayout(self.vBoxLayout)
        self.hBoxLayout1.addLayout(self.vBoxLayout2)
        self.centralWidget.setLayout(self.hBoxLayout1)
        self.setGeometry(300, 300, 300, 300)

        ## Configuring the plotting object.
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'r')
        pg.setConfigOption('leftButtonPan', False)

        self.label1 = QtGui.QLabel()
        self.label2 = QtGui.QLabel()
        self.label3 = QtGui.QLabel()
        self.label4 = QtGui.QLabel()
        self.label5 = QtGui.QLabel()
        self.label6 = QtGui.QLabel()

        self.label3.setText('Current Mode')
        self.label4.setText('FTP')
        self.label4.setStyleSheet('color : blue')

        self.label5.setText('Current Protocol')
        self.label6.setText(self.currentProtocol)
        self.label6.setStyleSheet('color: blue')

        self.btn = QtGui.QPushButton('Default')
        self.btn2 = QtGui.QPushButton('Connect')
        self.btn3 = QtGui.QPushButton('Pause Plot')
        self.btn4 = QtGui.QPushButton('Change Modes')
        self.btn5 = None
        self.btn6 = QtGui.QPushButton('Change Viewing Mode')
        self.btn7 = None
        self.btn8 = None

        self.btn.clicked.connect(self.buttonDefault)
        self.btn2.clicked.connect(self.protocolWindow)
        self.btn3.clicked.connect(self.buttonPause)
        self.btn4.clicked.connect(self.buttonChange)
        self.btn6.clicked.connect(self.fileViewingMode)

        self.p1 = pg.PlotWidget()  # Main plot
        self.p2 = pg.PlotWidget()  # Scrolling Plot
        self.p1.setLabel(axis='bottom', text='Time', units='s')
        self.p1.setLabel(axis='left', text='Voltage', units='mV')

        # Element for the threshold used in the continuous protocol.
        self.threshold = None

        self.p1.showGrid(x=False, y=True)

        ## Adding elements to main GUI.
        self.vBoxLayout.addWidget(self.label3)
        self.vBoxLayout.addWidget(self.label4)
        self.vBoxLayout.addWidget(self.btn4)
        self.vBoxLayout.addWidget(self.btn2)
        self.vBoxLayout.addWidget(self.btn3)
        self.vBoxLayout.addWidget(self.btn)
        self.vBoxLayout.addWidget(self.btn6)
        self.vBoxLayout.addWidget(self.label5)
        self.vBoxLayout.addWidget(self.label6)
        self.vBoxLayout.addWidget(self.label1)
        self.vBoxLayout.addWidget(self.label2)
        self.vBoxLayout.addStretch(1)
        self.setGeometry(300, 300, 1200, 800)

        self.vBoxLayout2.addWidget(self.p1, stretch=6)
        self.vBoxLayout2.addWidget(self.p2, stretch=1)

        self.btn.setEnabled(False)
        self.btn3.setEnabled(False)
        self.btn2.setEnabled(False)

        ## Call the funtion to start configuring the Hardware.
        self.readPelvIP()


    ## Functionthat checks if the pelvware has already been configured searching
    ## for the file that contains the pelvware IP.
    def readPelvIP(self):
        try:
            if sys.platform == 'linux' or sys.platform == 'linux2':
                f = open(os.getcwd()+'/bin/.pelvIp.file', 'r')
                self.pelvIP = f.readline().rstrip('\n')
            elif sys.platform == 'win32':
                f = open(os.getcwd()+'\\bin\\.pelvIp.file', 'r')
                self.pelvIP = f.readline().rstrip('\n')
        except IOError:
            print("Pelvware nao configurada!!")
            self.ipNotFoundDialog()

    ## In case the Pelvware isn't configured open a DIalog to start configuring.
    def ipNotFoundDialog(self):
        self.dialog = QtGui.QDialog()
        self.dialog.setFixedSize(300, 100)


        message = QtGui.QLabel('Pelvware not configured', self.dialog)
        button = QtGui.QPushButton('Configure', self.dialog)
        button.clicked.connect(self.dialogButton)

        message.move(83, 30)
        button.move(110, 50)

        self.dialog.setWindowTitle('Warning!!')
        self.dialog.exec_()

    def dialogButton(self):
        self.config()
        self.dialog.close()

    ## Used to discover the PC IP.
    def discoverIp(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 13000))
        self.HOST = s.getsockname()[0]
        s.close()

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.timer1.stop()
        self.fileQuit()

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
        self.fileName = QtGui.QFileDialog.getOpenFileName()
        self.plotFile()

    ## Function to make a static plot out of a file.
    def plotFile(self):
        # if self.fileName.contains(".csv"):
        #     file = csv.reader(self.fileName, delimiter=';')
        # else:
        file = open(self.fileName, 'r')

        self.p1.clear()
        self.p2.clear()

        self.p1.setDownsampling(mode='peak')
        self.p2.setDownsampling(mode='peak')

        self.p1.setClipToView(False)
        self.p2.setClipToView(False)

        self.x = []
        self.y = []
        self.separateData(file)

        print(self.x[-1])
        print(self.y[-1])
        self.p1.setXRange(0, self.x[-1] * 0.1, padding=0)

        self.curve1 = self.p1.plot(x=self.x, y=self.y, pen='r')
        self.curve2 = self.p2.plot(x=self.x, y=self.y, pen='r')
        self.zoomLinearRegion = pg.LinearRegionItem([0, (self.x[-1] * 0.1)])
        self.zoomLinearRegion.setZValue(-10)

        self.p2.addItem(self.zoomLinearRegion)

        self.p1.setYRange(0, self.rate, padding=0)


        self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
        self.p1.sigXRangeChanged.connect(self.updateRegion)

        self.btn.setDisabled(False)
        self.updatePlot()

    def plotPagedFile(self):
        try:
            self.removeScrollingPlot()
        except RuntimeError:
            print("ScrollingPlot Doesn't exist")
        file = open(self.fileName, 'r')

        self.p1.clear()
        self.p1.setDownsampling(mode='peak')
        self.p1.setClipToView(True)

        self.x = []
        self.y = []
        self.separateData(file)

        self.startX = 0.0
        self.endX = 45.0

        self.p1.setXRange(self.startX, self.endX, padding=0)
        self.p1.setYRange(0, self.rate, padding=0)

        self.curve1 = self.p1.plot(x=self.x, y=self.y, pen='r')

    def updatePlots(self):
        while True:
            time.sleep(0.1)
            self.time_dummy_value += 0.001
            self.dummy_value += 1
            self.y.append(self.time_dummy_value)
            self.x.append(self.dummy_value)

            self.p1.setXRange(0, self.x[-1] * 0.1, padding=0)
            self.p1.setYRange(0, self.rate, padding=0) ## Original should be 0.4 instead of 1024.

            self.curve1.setData(self.x, self.y)
            self.curve2.setData(self.x, self.y)

            # self.zoomLinearRegion.setRegion(
            #     [self.x[-1] - self.x[-1] * 0.1, self.x[-1]])

            self.updatePlot()
            # time.sleep(5)

    def updatePlot(self):
        self.p1.setXRange(*self.zoomLinearRegion.getRegion(), padding=0)

    def updateMainPlot(self):
        if self.x[-1] >= self.endX:
            self.startX = self.endX
            self.endX = self.startX + 45.0
            self.countX = self.countX + 1

            if self.countX == 1 and self.currentProtocol == 'Evaluative':
                self.protLinearRegion = pg.LinearRegionItem([self.startX + 25.0, self.startX + 35.0])
                self.p1.addItem(self.protLinearRegion)
            if self.countX == 2 and self.currentProtocol == 'Evaluative':
                self.protLinearRegion = pg.LinearRegionItem([self.startX + 25.0, self.startX + 35.0])
                self.p1.addItem(self.protLinearRegion)
            elif self.countX > 2:
                self.countX = 0
                self.statsCounter += 3
        # if self.currentProtocol == "Continuous":
        #     self.threshold = pg.InfiniteLine(pos=0.5, angle=0, movable=True)
        #     self.p1.addItem(self.threshold)
        #     print("OI")

    def updateRegion(self):
        if self.controleTeste:
            self.zoomLinearRegion.setRegion(self.p1.getViewBox().viewRange()[0])

    def writeFile(self, text):
        file = open('teste.log', 'a')
        file.write(text)
        file.write('\n')

    def removeScrollingPlot(self):
        self.p2.deleteLater()
        self.vBoxLayout.removeWidget(self.p2)

    def addScrollingPlot(self):
        self.p2 = pg.PlotWidget()
        self.vBoxLayout2.addWidget(self.p2, stretch=1)

        if self.readingMode:
            self.p2.setDownsampling(mode='peak')

            self.p2.setClipToView(True)

            self.curve2 = self.p2.plot(x=self.x, y=self.y, pen='r')
            # self.zoomLinearRegion = pg.LinearRegionItem([0, (self.x[-1] * 0.1)])
            self.zoomLinearRegion = pg.LinearRegionItem([0, 2])
            self.zoomLinearRegion.setZValue(-10)

            self.p2.addItem(self.zoomLinearRegion)

            self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
            self.p1.sigXRangeChanged.connect(self.updateRegion)
            self.updatePlot()


    def buttonDefault(self):
        if not self.readingMode:
            region = self.zoomLinearRegion.getRegion()
            new_region = [floor(region[0]), floor(region[0]) + (self.x[-1] * 0.1)]
            self.zoomLinearRegion.setRegion(new_region)

        self.updatePlot()
        self.p1.setYRange(0, self.rate, padding=0) # Original should be 0.4 instead of 1024


    def buttonPause(self):
        self.controleTeste = not self.controleTeste
        if not self.controleTeste:
            self.btn.setEnabled(False)
            self.removeScrollingPlot()
        else:
            self.btn.setDisabled(False)
            self.addScrollingPlot()


    def buttonChange(self):
        if not self.readingMode:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto('changeMode', (self.pelvIP, self.pelvPORT))
            sock.close()
            self.readingMode = not self.readingMode
            # self.rtState = not self.rtState
            self.btn5 = QtGui.QPushButton('Start Data Acquisition')
            self.btn5.clicked.connect(self.buttonPauseRT)
            self.btn2.setDisabled(False)
            self.vBoxLayout.addWidget(self.btn5)
            self.removeScrollingPlot()
            self.label4.setText("RT")
            self.label4.setStyleSheet('color : green')

        else:
            self.btn5.deleteLater()
            self.connected = 1
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto('changeMode', (self.pelvIP, self.pelvPORT))
            sock.close()
            self.protocolWindow()
            self.btn2.setEnabled(False)
            self.readingMode = not self.readingMode
            self.vBoxLayout.removeWidget(self.btn5)
            self.label4.setText("FTP")
            self.label4.setStyleSheet('color : blue')
            try:
                self.removeScrollingPlot()
            except:
                print("Grafico inexistente")
            self.addScrollingPlot()



    def buttonPauseRT(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.rtState:
            sock.sendto('pauseRT', (self.pelvIP, self.pelvPORT))
            self.btn5.setText('Start Data Acquisition')
            self.addScrollingPlot()

        else:
            sock.sendto('startRT', (self.pelvIP, self.pelvPORT))
            self.btn5.setText('Pause Data Acquisition')
            try:
                self.removeScrollingPlot()
            except:
                print('Grafico inexistente')


        self.rtState = not self.rtState


    def buttonConnect(self):
        if self.connected == 0:
            self.connected = 1
            self.btn3.setDisabled(False)
            # self.controleTeste = 0
            self.x = [0]
            self.y = [0]
            self.endX = 45.0
            self.startX = 0.0
            # self.x.append(0)
            # self.y.append(0.0)
            self.p1.clear()
            # self.p2.clear()

            self.p1.setDownsampling(mode='peak')
            # self.p2.setDownsampling(mode='peak')

            self.p1.setClipToView(True)
            # self.p2.setClipToView(True)

            self.p1.setXRange(self.startX, self.endX, padding=0)

            self.curve1 = self.p1.plot(x=self.x, y=self.y, pen='r')

            self.label1.setText('Status da Conexao')

            if self.currentProtocol == "Continuous":
                self.threshold = pg.InfiniteLine(pos=500, angle=0, movable=True, pen='b')
                self.p1.addItem(self.threshold, ignoreBounds=True)

            self.timer1.start(1)

            try:
                self.rcvThread.start()
                self.processingThread.start()
                self.plotThread.start()
            except:
                print('threads already running')

        else:
            # self.controleTeste = not self.controleTeste
            # try:
            #     self.buttonPause()
            # except:
            #     print("Grafico despausado")
            self.btn.setEnabled(False)
            self.btn3.setEnabled(False)
            self.connected = 0

    def udpThread(self):
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(self.orig)
        self.udp.settimeout(2)
        while self.connected == 1:
            # ready = select.select()
            # self.startTime = time.time()
            try:
                msg, client = self.udp.recvfrom(20)
                self.hasData.acquire()
                self.dataToBeProcessed.append(msg)
                # print(self.dataToBeProcessed)
                self.hasData.notify()
                self.hasData.release()

            except:
                print("Timed Out")
        self.udp.close()


    def processDataThread(self):
        while self.connected == 1:
            # if self.connected == 1:
            # print("Processando")
            self.hasData.acquire()
            self.hasProcData.acquire()
            if not self.dataToBeProcessed:
                self.hasData.wait()

            self.startTime = time.time()
            data = self.dataToBeProcessed.pop()
            a, b = data.split(';')
            if (float(a)) > self.x[-1]:
                self.x.append(float(a)/1000) ## float(a)/1000 e o correto.
                self.y.append(float(b))
            print(float(a))
            self.hasNew = True
            self.hasProcData.notify()
            self.hasProcData.release()
            self.hasData.release()
            time.sleep(0.021)

    def pltThread(self):
        while self.connected == 1:
            self.hasProcData.acquire()

            if not self.hasNew:
                self.hasProcData.wait()

            if (len(self.x) == len(self.y)) and (len(self.y) != 0) and not self.controleTeste:
                self.p1.setXRange(self.startX, self.endX, padding=0)
                self.p1.setYRange(0, self.rate, padding=0)

                try:
                    self.curve1.setData(self.x, self.y)
                    # self.curve2.setData(self.x, self.y)

                except:
                    print("Algo deu errado!")
                print(self.currentProtocol)
                self.updateMainPlot()
                self.hasNew = False
                self.hasProcData.release()
                self.testFunc()

                time.sleep(0.05)
            else:
                print("Tamanhos diferentes!")

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
            win = QtGui.QDialog()
            win.setGeometry(400, 300, 200, 100)
            layout = QtGui.QVBoxLayout()

            self.b1 = QtGui.QRadioButton("Continuous")
            self.b1.setChecked(True)
            layout.addWidget(self.b1)

            self.b2 = QtGui.QRadioButton("Evaluative")

            btn = QtGui.QPushButton('Ok')
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
        fileName = QtGui.QFileDialog.getSaveFileName(self, "Save File", "Files (*.csv)")
        print(fileName)
        with open(fileName, 'w') as csvfile:
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
        self.p1.setXRange(self.startX, self.endX, padding=0)

    def previousPage(self):
        self.endX = self.startX
        self.startX = self.endX - 45.0
        self.p1.setXRange(self.startX, self.endX, padding=0)

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
            self.addScrollingPlot()
            self.plotFile()
        elif self.viewingMode == False:
            self.viewingMode = not self.viewingMode
            if not self.rtState:
                self.btn6 = QtGui.QPushButton('<< Previous Page')
                self.btn7 = QtGui.QPushButton('>> Next Page')

                self.btn6.clicked.connect(self.previousPage)
                self.btn7.clicked.connect(self.nextPage)

                self.vBoxLayout.addWidget(self.btn6)
                self.vBoxLayout.addWidget(self.btn7)

            self.plotPagedFile()


qApp = QtGui.QApplication(sys.argv)

applicationWindow = ApplicationWindow()
applicationWindow.show()
sys.exit(qApp.exec_())
