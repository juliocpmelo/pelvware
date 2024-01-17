from concurrent.futures import thread
import sys
import time
from PelvwareProtocol import PelvwareCommands
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import pyqtSignal
from math import floor
from threading import Thread, Condition, Timer
from pyqtgraph.GraphicsScene import exportDialog

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



DEFAULT_VIEW_SECS = 10


class ApplicationWindow(QtWidgets.QMainWindow, PelvwareSerialHandler):

    data_received_sig = pyqtSignal([float, float, float])
    pelvware_connect_sig = pyqtSignal()
    pelvware_disconnect_sig = pyqtSignal()

    boardTestMode = False
    localTestMode = False
    sessionStoped = False
    analysisVisible = False

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
        self.current_view_secs = DEFAULT_VIEW_SECS

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
        self.x = np.zeros(1)
        self.y = np.zeros(1)
        self.dummy_value = 0
        self.time_dummy_value = 0.0

        # Variables used to mark the range of the x-axis.
        self.endX = 45
        self.startX = 0
        self.countX = 0

        self.statsCounter = 0
        self.statistics = []

        # Creation of the menu File
        self.file_menu = QtWidgets.QMenu('&Opções', self)
        self.file_menu.addAction('&Abrir Sessão', self.openSession)
        self.file_menu.addAction('&Salvar Sessão', self.saveSession)
        self.file_menu.addAction('&Limpar Dados', self.clearDataAction)

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

        # Main plot
        self.mainPlot = pg.PlotWidget(enableMenu=False)  
        self.mainPlot.setLabel(axis='bottom', text='Time', units='sec')
        self.mainPlot.setLabel(axis='left', text='Voltage', units='volt')
        self.mainPlot.showGrid(x=False, y=True)
        self.vBoxLayout2.addWidget(self.mainPlot, stretch=6)
        
        # Scrolling Plot
        self.scrollingPlot = pg.PlotWidget(enableMenu=False,lockAspect=False)  
        self.scrollingPlot.setLabel(axis='bottom', text='Time', units='sec')
        self.scrollingPlot.setLabel(axis='left', text='Voltage', units='volt')
        self.scrollingPlot.showGrid(x=False, y=True)
        self.vBoxLayout2.addWidget(self.scrollingPlot, stretch=1)
        
        # Scrolling Plot Selection Rect
        self.scrollingPlotSelectRect = pg.LinearRegionItem(values=(-self.current_view_secs/2, self.current_view_secs/2))
        self.scrollingPlotSelectRect.sigRegionChanged.connect(self.scrollingPlotSelectChaned)
        
        #connection status label
        self.label3 = QtWidgets.QLabel()
        self.label3.setText('Status de Conexão:')
        self.vBoxLayout.addWidget(self.label3)
        self.connectionStatusLabel = QtWidgets.QLabel()
        self.vBoxLayout.addWidget(self.connectionStatusLabel)

        #board test mode button
        if self.boardTestMode:
            self.testModeBtn = QtWidgets.QPushButton('Toogle Test Mode')
            self.testModeBtn.clicked.connect(self.toogleTestMode)
            self.vBoxLayout.addWidget(self.testModeBtn)
            self.testModeBtn.setEnabled(False)

        #hold plot
        self.holdPlotButton = QtWidgets.QPushButton('Parar de Acompanhar')
        self.holdPlotButton.clicked.connect(lambda: self.holdPlot())
        self.vBoxLayout.addWidget(self.holdPlotButton)

        #stop session button
        self.stopSessionBtn = QtWidgets.QPushButton('Finalizar Sessão')
        self.stopSessionBtn.clicked.connect(lambda : self.stopSession()) 
        self.vBoxLayout.addWidget(self.stopSessionBtn)
        
        #add analysis
        self.addAnalysisBtn = QtWidgets.QPushButton('Mostrar Análise')
        self.addAnalysisBtn.clicked.connect(self.showAnalysis)
        self.vBoxLayout.addWidget(self.addAnalysisBtn)

        #analysis rectangle and display info
        self.analysisRect = pg.LinearRegionItem(values=(-DEFAULT_VIEW_SECS/2, DEFAULT_VIEW_SECS/2), brush=pg.mkBrush(200,200,0,100))
        self.analysisRect.sigRegionChangeFinished.connect(self.analysisRectChaned)
        self.analysisText = pg.TextItem(text=self.getAnalysisText(0,0,0,0,0), color=(0,0,0))
        self.analysisRect.sigRegionChanged.connect(self.updateAnalysisTextPos)
        self.mainPlot.getViewBox().sigRangeChanged.connect(self.updateAnalysisTextPos)

        self.vBoxLayout.addStretch(1)
        self.setGeometry(300, 300, 1200, 800)


        self.holdPlotButton.setEnabled(False)
        self.data_received_sig.connect(self.onDataReceived)
        self.pelvware_connect_sig.connect(self.onPelvwareConnect)
        self.pelvware_disconnect_sig.connect(self.onPelvwareDisconnect)

        self.clearData()
        self.setConnectionStatus(False)
        
        self.plotPaused = False
        
        self.serialManager = PelvwareSerialManager()
        self.serialManager.addSerialHandler(self)

    def updateAnalysisTextPos(self):
        x_range, y_range = self.mainPlot.viewRange()
        y_pos = y_range[0] + 0.9 * (y_range[1] - y_range[0])
        rect_x = self.analysisRect.getRegion()[0]
        self.analysisText.setPos(rect_x, y_pos)

    def getValueAndUint(self,val):
        if 1 > val and val > 0:
            return '{} mV'.format(round(val * 1000))
        else:
            return '{:.3f} V'.format(val)
        
    def getAnalysisText(self, std, max, min, avg, qavg):
        
        return 'std: {}\nmax: {}\nmin: {}\navg: {}\nqavg: {}'.format(
            self.getValueAndUint(std), 
            self.getValueAndUint(max), 
            self.getValueAndUint(min), 
            self.getValueAndUint(avg), 
            self.getValueAndUint(qavg))

    def analysisRectChaned(self, rect):
        reg = rect.getRegion()
        mask = (self.x >= reg[0]) & (self.x <= reg[1])
        try:
            std = np.std(self.y[mask])
            max = np.max(self.y[mask])
            min = np.min(self.y[mask])
            avg = np.average(self.y[mask])
            qavg = np.sqrt(np.mean(np.square(self.y[mask])))


        except:
            std = 0
            max = 0
            min = 0
            avg = 0
            qavg = 0
        self.analysisText.setText(text=self.getAnalysisText(std,max,min,avg,qavg))

    
    def scrollingPlotSelectChaned(self, rect):
        reg = rect.getRegion()
        self.updateMainPlotView(reg)
        

    #Process the command line options
    def setCommandOptions(self, cmdOptions):
        #enables board test mode, user can signal board to generate test signal
        self.boardTestMode = cmdOptions.boardTestMode

        #stops serial serial manager and starts local test mode
        #in this mode we can debug the plot by using local generated data
        self.localTestMode = cmdOptions.localTestMode
        if self.localTestMode :
            self.serialManager.stopAllThreads()
            self.degree = 0
            self.start_time = time.time() * 1000
            self.last_x = 0
            self.fake_connection = Timer(1, self.fakeConnectionGenerator, [])
            self.fake_connection.start()
            
    #plot
    def plotData(self, data_x, data_y):
        self.x = data_x
        self.y = data_y
        self.endX = self.current_view_secs
        self.startX = 0.0

        self.mainPlot.clear()
        self.mainPlot.setXRange(self.startX, self.endX, padding=0)
        self.mainPlot.setYRange(0, self.rate, padding=0)
        self.mainGraphCurve = self.mainPlot.plot(x=self.x, y=self.y, pen='r')

        self.scrollingPlot.clear()
        self.scrollingPlotCurve = self.scrollingPlot.plot(x=self.x, y=self.y, pen='r')
        self.scrollingPlotSelectRect.setRegion((self.x[-1] - self.current_view_secs/2,
                                                self.x[-1] + self.current_view_secs/2))
        self.scrollingPlot.addItem(self.scrollingPlotSelectRect)

    def showConfirmDialog(self, confirmText):
        msgBox = QtWidgets.QMessageBox(
            QMessageBox.Question,
            "Tem certeza?",
            confirmText,
            parent=self)
        msgBox.setDefaultButton(QMessageBox.No)
        yes = msgBox.addButton('Sim', QMessageBox.ButtonRole.YesRole)
        msgBox.addButton('Não', QMessageBox.ButtonRole.NoRole)
        msgBox.exec()
        if msgBox.clickedButton() == yes:
            return True
        return False

    def clearDataAction(self):
        if self.showConfirmDialog("Tem certeza que quer limpar os dados? As informações serão perdidas!"):
            self.clearData()

    def clearData(self):
        
        self.plotData(np.zeros(1),np.zeros(1))
        
    def toogleTestMode(self):
        if self.serialManager is not None:
            self.serialManager.sendCommand(PelvwareCommands.TOOGLE_TEST_MODE)
                
    def closeEvent(self, event):
        if self.showConfirmDialog("Tem certeza que quer fechar? As informações serão perdidas!"):
            if self.serialManager is not None:
                self.serialManager.stopAllThreads()
            if self.localTestMode :
                self.fake_data_timer.cancel()
                self.fake_data_timer.join()
        else:
            event.ignore()

    def updateMainPlotView(self, region=None):
        #window will follow if the current sample is greater than half of visible window
        if self.x[-1] >= self.current_view_secs/2 and not self.plotPaused:
            self.startX = self.x[-1] - self.current_view_secs/2
            self.endX = self.x[-1] + self.current_view_secs/2
            self.mainPlot.setXRange(self.startX, self.endX, padding=0)
            self.scrollingPlotSelectRect.setRegion((self.x[-1] - self.current_view_secs/2,
                                                self.x[-1] + self.current_view_secs/2))
        #when plot is paused we can still scroll using the scrolling area
        elif region is not None: 
            self.current_view_secs = region[1] - region[0]
            self.startX = region[0]
            self.endX = region[1]
            self.mainPlot.setXRange(self.startX, self.endX, padding=0)

    def showScrollingPlot(self):
        self.scrollingPlot.show()
        self.scrollingPlotSelectRect.setRegion((self.x[-1] - self.current_view_secs/2,
                                                self.x[-1] + self.current_view_secs/2))

    def holdPlot(self, force=None):
        if force is None:
            self.plotPaused = not self.plotPaused
        else:
            self.plotPaused = force
        
        if self.plotPaused :
            self.holdPlotButton.setText('Acompanhar Gráfico')
        else:
            self.holdPlotButton.setText('Parar de Acompanhar')


    @QtCore.pyqtSlot(float, float, float)
    def onDataReceived(self, time, volts, time_between_messages):
        if not self.sessionStoped : #Ignore data if the session has ended
            if len(self.x) == 0 or time > self.x[-1] :
                #print('appending {} {} '.format(x_val, y_val))
                self.x = np.append(self.x, time/1000) #time is received in millisecs
                self.y = np.append(self.y, volts) #y val is received in volts
                self.refreshCurves()
                self.updateMainPlotView()
    
    def refreshCurves(self):
        #add to main plot            
        self.mainGraphCurve.setData(self.x, self.y)
        #add to scrolling plot
        self.scrollingPlotCurve.setData(self.x, self.y)

    def setConnectionStatus(self, connected):
        if connected :
            self.connected = 1
            if self.boardTestMode :
                self.testModeBtn.setEnabled(True)
            self.holdPlotButton.setEnabled(True)
            self.connectionStatusLabel.setText('Conectado')
            self.connectionStatusLabel.setStyleSheet('color : green')
        else:
            self.connected = 0
            self.holdPlotButton.setEnabled(False)
            if self.boardTestMode :
                self.testModeBtn.setEnabled(False)
            self.connectionStatusLabel.setText('Desconectado')
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

    def showAnalysis(self):
        self.analysisVisible = not self.analysisVisible
        if self.analysisVisible :
            self.addAnalysisBtn.setText('Esconder Análise')
            self.mainPlot.addItem(self.analysisRect)
            self.mainPlot.addItem(self.analysisText)
        else:
            self.mainPlot.removeItem(self.analysisRect)
            self.mainPlot.removeItem(self.analysisText)
            self.addAnalysisBtn.setText('Mostrar Análise')
        

    def stopSession(self, force = None):
        if force is None :
            self.sessionStoped = not self.sessionStoped 
        else:
            self.sessionStoped = force
        
        if not self.sessionStoped :
            self.holdPlot(force=False)
            self.stopSessionBtn.setText("Finalizar Sessão")
        else:
            self.holdPlot(force=True)
            self.stopSessionBtn.setText("Reiniciar Sessão")

    ## Function to make a static plot out of a file.
    def openSession(self):
        self.stopSession(force=True)
        self.holdPlot(force=True)
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName()

        if fileName :
            self.clearData()
            np_x, np_y = np.loadtxt(fileName, delimiter=',', unpack=True)
            self.plotData(np_x, np_y)
            self.updateMainPlotView()

    def saveSession(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(parent=self, caption="Salvar Arquivo",
                                       filter="CSV Files (*.csv)")
        if fileName : #arquivo selecionado / nome digitado
            np.savetxt(fileName, [p for p in zip(self.x, self.y)], delimiter=',')


import argparse

def parseCommandArgs():
    parser = argparse.ArgumentParser(description='Pelvware Command Line')
    parser.add_argument('--localTestMode', action='store_true')
    parser.add_argument('--boardTestMode', action='store_true')
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


