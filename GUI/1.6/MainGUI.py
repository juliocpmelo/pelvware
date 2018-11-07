import sys
import time
from PyQt4 import QtGui, QtCore
from math import floor
from threading import Thread, Condition
import pyqtgraph as pg
import numpy as np
import socket
import select
import ConfigGUI


class ApplicationWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Pelvware")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.connectionHealth)        

        # Threads Controllers and Condiotions.
        self.connected = 0
        self.controleTeste = 0

        self.hasData = Condition()
        self.hasProcData = Condition()
        self.hasNew = False

        self.startTime = time.time()

        # File to be Plotted Statically.
        self.fileName = ''

        # Network Configuration of Host and Port.
        # self.HOST = socket.gethostbyname(socket.gethostname()) ## estranhamente esta funcao deixou de funcionar na minha vm por isso a comentei.
        self.HOST = '192.168.0.43'
        self.PORT = 5000

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

        self.btn = QtGui.QPushButton('Default')
        self.btn2 = QtGui.QPushButton('Connect')
        self.btn3 = QtGui.QPushButton('Pause')

        self.btn.clicked.connect(self.buttonDefault)
        self.btn2.clicked.connect(self.buttonConnect)
        self.btn3.clicked.connect(self.buttonPause)

        self.p1 = pg.PlotWidget()  # Main plot
        self.p2 = pg.PlotWidget()  # Scrolling Plot

        self.p1.showGrid(x=False, y=True)

        self.vBoxLayout.addWidget(self.btn)
        self.vBoxLayout.addWidget(self.btn2)
        self.vBoxLayout.addWidget(self.btn3)
        self.vBoxLayout.addWidget(self.label1)
        self.vBoxLayout.addWidget(self.label2)
        self.vBoxLayout.addStretch(1)
        self.setGeometry(300, 300, 1200, 800)

        self.vBoxLayout2.addWidget(self.p1, stretch=6)
        self.vBoxLayout2.addWidget(self.p2, stretch=1)

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
            self.p1.setYRange(0, 1024, padding=0) ## Original should be 0.4 instead of 1024.

            self.curve1.setData(self.x, self.y)
            self.curve2.setData(self.x, self.y)

            self.zoomLinearRegion.setRegion(
                [self.x[-1] - self.x[-1] * 0.1, self.x[-1]])

            self.updatePlot()
            # time.sleep(5)

    def updatePlot(self):
        self.p1.setXRange(*self.zoomLinearRegion.getRegion(), padding=0)

    def updateRegion(self):
        if self.controleTeste == 0:
            self.zoomLinearRegion.setRegion(self.p1.getViewBox().viewRange()[0])

    def writeFile(self, text):
        file = open('teste.log', 'a')
        file.write(text)
        file.write('\n')

    def buttonDefault(self):
        region = self.zoomLinearRegion.getRegion()
        new_region = [floor(region[0]), floor(region[0]) + (self.x[-1] * 0.1)]
        self.zoomLinearRegion.setRegion(new_region)
        self.p1.setYRange(0, 1024, padding=0) # Original should be 0.4 instead of 1024
        self.updatePlot()

    def buttonPause(self):
        if self.controleTeste == 0:
            self.controleTeste = 1

        else:
            self.controleTeste = 0

    def buttonConnect(self):
        if self.connected == 0:
            self.connected = 1
            # self.controleTeste = 0
            self.x = [0]
            self.y = [0]
            # self.x.append(0)
            # self.y.append(0.0)
            self.p1.clear()
            self.p2.clear()

            self.p1.setDownsampling(mode='peak')
            self.p2.setDownsampling(mode='peak')

            self.p1.setClipToView(True)
            self.p2.setClipToView(True)

            self.curve1 = self.p1.plot(x=self.x, y=self.y, pen='r')
            self.curve2 = self.p2.plot(x=self.x, y=self.y, pen='r')
            self.zoomLinearRegion = pg.LinearRegionItem(
                [0, (0 * 0.1)])
            self.zoomLinearRegion.setZValue(-10)

            self.p2.addItem(self.zoomLinearRegion)

            self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
            self.p1.sigXRangeChanged.connect(self.updateRegion)

            self.label1.setText('Status da Conexao')

            # timer = QtCore.QTimer()
            # timer.timeout.connect(connectionHealth)
            self.timer.start(1)

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
            print(self.connected)
            self.connected = 0

    def udpThread(self):
        print(self.HOST)
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        orig = (self.HOST, self.PORT)
        udp.bind(orig)
        udp.settimeout(2)
        while self.connected == 1:
            # ready = select.select()
            # self.startTime = time.time()
            try:
                msg, client = udp.recvfrom(20)
                self.hasData.acquire()
                self.dataToBeProcessed.append(msg)
                # print(self.dataToBeProcessed)
                self.hasData.notify()
                self.hasData.release()

            except:
                print("Timed Out")
        udp.close()

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
            self.x.append(int(a))
            self.y.append(float(b))
            #print(self.x)
            self.hasNew = True
            self.hasProcData.notify()
            self.hasProcData.release()
            self.hasData.release()
            time.sleep(0.021)

    # needs to change from the dummy values to the udp data. #
    def pltThread(self):
        while self.connected == 1:
            # if self.connected == 1:
            self.hasProcData.acquire()

            # print("Teste")

            # if not self.x and not self.y:
            #     self.hasProcData.wait()

            if not self.hasNew:
                self.hasProcData.wait()

            self.p1.setXRange(0, self.x[-1] * 0.1, padding=0)
            self.p1.setYRange(0, 1024, padding=0)

            self.curve1.setData(self.x, self.y)
            self.curve2.setData(self.x, self.y)

            if self.controleTeste == 0:
                self.zoomLinearRegion.setRegion(
                    [self.x[-1] - self.x[-1] * 0.1, self.x[-1]])

            self.updatePlot()
            self.hasNew = False
            self.hasProcData.release()

            time.sleep(0.05)

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
        configWindow = ConfigGUI.window()
        # configWindow.show()
        # configWindow.exec_()

qApp = QtGui.QApplication(sys.argv)

applicationWindow = ApplicationWindow()
applicationWindow.show()
sys.exit(qApp.exec_())
