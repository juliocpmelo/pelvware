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

class ApplicationWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Pelvware")

        self.configWindow = None
        self.dialog = None

        self.rate = 0.4

        self.timer1 = QtCore.QTimer()
        self.timerRcv = QtCore.QTimer()
        self.timerProc = QtCore.QTimer()
        self.timerPlt = QtCore.QTimer()

        self.timer1.timeout.connect(self.connectionHealth)
        self.timerRcv.timeout.connect(self.udpThread)
        self.timerProc.timeout.connect(self.processDataThread)
        self.timerPlt.timeout.connect(self.pltThread)

        # Threads Controllers and Condiotions.
        self.connected = 0
        self.controleTeste = False ## Controller of the pause function. 0 = running, and 1 = paused

        self.hasData = Condition()
        self.hasProcData = Condition()
        self.hasNew = False

        self.startTime = time.time()

        # File to be Plotted Statically.
        self.fileName = ''

        # Info on the current Mode, if it's the RT we also have the acquisition state.
        # readingMode (true = RT, false = FTP) always starts with false.
        # rtState (true = Active, false = Inactive) always starts inactive.
        self.readingMode = False;
        self.rtState = False


        # Network Configuration of Host and Port.
        # self.HOST = socket.gethostbyname(socket.gethostname()) ## estranhamente esta funcao deixou de funcionar na minha vm por isso a comentei.
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

        self.hBoxLayout1 = QtGui.QHBoxLayout()
        self.vBoxLayout = QtGui.QVBoxLayout()
        self.vBoxLayout2 = QtGui.QVBoxLayout()

        self.hBoxLayout1.addLayout(self.vBoxLayout)
        self.hBoxLayout1.addLayout(self.vBoxLayout2)
        self.centralWidget.setLayout(self.hBoxLayout1)
        self.setGeometry(300, 300, 300, 300)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'r')
        pg.setConfigOption('leftButtonPan', False)

        self.label1 = QtGui.QLabel()
        self.label2 = QtGui.QLabel()
        self.label3 = QtGui.QLabel()
        self.label4 = QtGui.QLabel()

        self.label3.setText('Modo Atual')
        self.label4.setText('FTP')
        self.label4.setStyleSheet('color : blue')

        self.btn = QtGui.QPushButton('Default')
        self.btn2 = QtGui.QPushButton('Connect')
        self.btn3 = QtGui.QPushButton('Pause Plot')
        self.btn4 = QtGui.QPushButton('Change Modes')
        self.btn5 = None
        # This Button should only be active when the probe is the RT Mode
        # self.btn5 = QtGui.QPushButton('Pause Data Acquisition')

        self.btn.clicked.connect(self.buttonDefault)
        self.btn2.clicked.connect(self.buttonConnect)
        self.btn3.clicked.connect(self.buttonPause)
        self.btn4.clicked.connect(self.buttonChange)
        # self.btn5.clicked.connect(self.buttonPauseRT)

        self.p1 = pg.PlotWidget()  # Main plot
        self.p2 = pg.PlotWidget()  # Scrolling Plot

        self.p1.showGrid(x=False, y=True)

        self.vBoxLayout.addWidget(self.label3)
        self.vBoxLayout.addWidget(self.label4)
        self.vBoxLayout.addWidget(self.btn4)
        self.vBoxLayout.addWidget(self.btn2)
        self.vBoxLayout.addWidget(self.btn3)
        self.vBoxLayout.addWidget(self.btn)
        self.vBoxLayout.addWidget(self.label1)
        self.vBoxLayout.addWidget(self.label2)
        self.vBoxLayout.addStretch(1)
        self.setGeometry(300, 300, 1200, 800)

        self.vBoxLayout2.addWidget(self.p1, stretch=6)
        self.vBoxLayout2.addWidget(self.p2, stretch=1)

        self.btn.setEnabled(False)
        self.btn3.setEnabled(False)
        self.btn2.setEnabled(False)

        self.readPelvIP()


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

    def discoverIp(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 13000))
        self.HOST = s.getsockname()[0]
        s.close()

    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        self.fileQuit()

    def separateData(self, file):
        for line in file:
            a, b = line.split(';')
            self.x.append(a)
            self.y.append(b)

        self.x = list(map(int, self.x))
        self.y = list(map(float, self.y))

        self.y = map(lambda a: (((a * (3.2 / 1023)) / 10350) * 1000), self.y)

    def selectFile(self):
        self.fileName = QtGui.QFileDialog.getOpenFileName()
        self.plotFile()

    def plotFile(self):
        file = open(self.fileName, 'r')

        # if self.count == 0:
        #     self.vBoxLayout.addWidget(self.btn)
        #     self.vBoxLayout.addWidget(self.btn2)
        #     self.vBoxLayout.addStretch(1)
        #     self.setGeometry(300, 300, 1200, 800)
        #     self.count += 1

        self.p1.clear()
        self.p2.clear()

        self.p1.setDownsampling(mode='peak')
        self.p2.setDownsampling(mode='peak')

        self.p1.setClipToView(True)
        self.p2.setClipToView(True)

        self.x = []
        self.y = []
        self.separateData(file)

        self.p1.setXRange(0, self.x[-1] * 0.1, padding=0)
        self.p1.setYRange(0, 0.4, padding=0)

        self.curve1 = self.p1.plot(x=self.x, y=self.y, pen='r')
        self.curve2 = self.p2.plot(x=self.x, y=self.y, pen='r')
        self.zoomLinearRegion = pg.LinearRegionItem([0, (self.x[-1] * 0.1)])
        self.zoomLinearRegion.setZValue(-10)

        self.p2.addItem(self.zoomLinearRegion)

        # self.vBoxLayout2.addWidget(self.p1, stretch=6)
        # self.vBoxLayout2.addWidget(self.p2, stretch=1)

        self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
        self.p1.sigXRangeChanged.connect(self.updateRegion)
        self.updatePlot()

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

            self.zoomLinearRegion.setRegion(
                [self.x[-1] - self.x[-1] * 0.1, self.x[-1]])

            self.updatePlot()
            # time.sleep(5)

    def updatePlot(self):
        self.p1.setXRange(*self.zoomLinearRegion.getRegion(), padding=0)

    def updateRegion(self):
        if self.controleTeste:
            print(self.controleTeste)
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
            self.btn5 = QtGui.QPushButton('Pause Data Acquisition')
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
            self.buttonConnect()
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
            self.addScrollingPlot()
        else:
            sock.sendto('startRT', (self.pelvIP, self.pelvPORT))
            self.removeScrollingPlot()

        self.rtState = not self.rtState


    def buttonConnect(self):
        if self.connected == 0:
            self.connected = 1
            self.btn3.setDisabled(False)
            # self.controleTeste = 0
            self.x = [0]
            self.y = [0]
            # self.x.append(0)
            # self.y.append(0.0)
            self.p1.clear()
            # self.p2.clear()

            self.p1.setDownsampling(mode='peak')
            # self.p2.setDownsampling(mode='peak')

            self.p1.setClipToView(True)
            # self.p2.setClipToView(True)

            self.curve1 = self.p1.plot(x=self.x, y=self.y, pen='r')
            # self.curve2 = self.p2.plot(x=self.x, y=self.y, pen='r')
            # self.zoomLinearRegion = pg.LinearRegionItem(
            #     [0, (0 * 0.1)])
            # self.zoomLinearRegion.setZValue(-10)

            # self.p2.addItem(self.zoomLinearRegion)

            # self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
            # self.p1.sigXRangeChanged.connect(self.updateRegion)

            self.label1.setText('Status da Conexao')

            # timer = QtCore.QTimer()
            # timer.timeout.connect(connectionHealth)
            self.timer1.start(1)
            # self.timerRcv.start(0.01)
            # self.timerProc.start(0.021)
            # self.timerPlt.start(0.05)

                # if timer.isActive():
                #     print("Rodou")

            rcvThread = Thread(target=self.udpThread)
            processingThread = Thread(target=self.processDataThread)
            pltThread = Thread(target=self.pltThread)
            # thread = Thread(target=self.connectionHealth)

            rcvThread.start()
            processingThread.start()
            pltThread.start()
            # thread.start()

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
        print(self.HOST)
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
        print("udp closing ")


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
            self.x.append(int(a) * 1000)
            self.y.append(float(b))
            #print(self.x)
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
                self.p1.setXRange(0, self.x[-1] * 0.1, padding=0)
                self.p1.setYRange(0, self.rate, padding=0)

                try:
                    self.curve1.setData(self.x, self.y)
                    # self.curve2.setData(self.x, self.y)

                except:
                    print("Algo deu errado!")
                # if self.controleTeste == 0:
                #     self.zoomLinearRegion.setRegion(
                #         [self.x[-1] - self.x[-1] * 0.1, self.x[-1]])

                # self.updatePlot()
                self.hasNew = False
                self.hasProcData.release()

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

    # def updateModeLabel():
    #     if

qApp = QtGui.QApplication(sys.argv)

applicationWindow = ApplicationWindow()
applicationWindow.show()
sys.exit(qApp.exec_())
