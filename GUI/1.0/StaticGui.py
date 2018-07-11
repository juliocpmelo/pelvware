import sys
from PyQt4 import QtGui, QtCore
from math import floor
import pyqtgraph as pg


class ApplicationWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Pelvware")

        self.count = 0

        # Connecting to the FTPServer

        self.fileName = ''

        # Data to be plotted
        self.x = []
        self.y = []

        # Creation of the menu File
        self.file_menu = QtGui.QMenu('&File', self)
        self.file_menu.addAction('&Open', self.selectFile)
        self.file_menu.addAction('&Save')
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

        self.btn = QtGui.QPushButton('Default')
        # self.btn2 = QtGui.QPushButton('Teste')

        self.btn.clicked.connect(self.buttonDefault)

        self.p1 = pg.PlotWidget()  # Main plot
        self.p2 = pg.PlotWidget()  # Scrolling Plot

        self.p1.showGrid(x=False, y=True)

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

    def selectFile(self):
        self.fileName = QtGui.QFileDialog.getOpenFileName()
        self.plotFile()

    def plotFile(self):
        file = open(self.fileName, 'r')

        if self.count == 0:
            self.vBoxLayout.addWidget(self.btn)
            # self.vBoxLayout.addWidget(self.btn2)
            self.vBoxLayout.addStretch(1)
            self.setGeometry(300, 300, 1200, 800)
            self.count += 1

        self.p1.clear()
        self.p2.clear()

        self.x = []
        self.y = []
        self.separateData(file)

        self.p1.setXRange(0, self.x[-1] * 0.1, padding=0)
        self.p1.setYRange(0, 1000, padding=0)

        self.p1.plot(x=self.x, y=self.y, pen='r')
        self.p2.plot(x=self.x, y=self.y, pen='r')

        self.zoomLinearRegion = pg.LinearRegionItem([0, (self.x[-1] * 0.1)])
        self.zoomLinearRegion.setZValue(-10)

        self.p2.addItem(self.zoomLinearRegion)

        self.vBoxLayout2.addWidget(self.p1, stretch=6)
        self.vBoxLayout2.addWidget(self.p2, stretch=1)

        self.zoomLinearRegion.sigRegionChanged.connect(self.updatePlot)
        self.p1.sigXRangeChanged.connect(self.updateRegion)
        self.updatePlot()

    def updatePlot(self):
        self.p1.setXRange(*self.zoomLinearRegion.getRegion(), padding=0)

    def updateRegion(self):
        self.zoomLinearRegion.setRegion(self.p1.getViewBox().viewRange()[0])

    def writeFile(self, text):
        file = open('teste.log', 'a')
        file.write(text)
        file.write('\n')

    def buttonDefault(self):
        region = self.zoomLinearRegion.getRegion()
        new_region = [floor(region[0]), floor(region[0]) + (self.x[-1] * 0.1)]
        self.zoomLinearRegion.setRegion(new_region)
        self.p1.setYRange(0, 1000, padding=0)
        self.updatePlot()


qApp = QtGui.QApplication(sys.argv)

applicationWindow = ApplicationWindow()
applicationWindow.show()
sys.exit(qApp.exec_())
