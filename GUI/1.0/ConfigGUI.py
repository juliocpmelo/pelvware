import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *


def window():
    app = QApplication(sys.argv)
    win = QWidget()

    l1 = QLabel("Nome")
    nm = QLineEdit()


    l2 = QLabel("WiFi SSID")
    add1 = QComboBox()

    l3 = QLabel("WiFi Password")
    add2 = QLineEdit()
    add2.setEchoMode(QLineEdit.Password)

    l4 = QLabel("Porta Serial")
    add3 = QComboBox()

    fbox = QFormLayout()
    vbox1 = QVBoxLayout()
    vbox2 = QVBoxLayout()
    vbox3 = QVBoxLayout()

    fbox.addRow(l1, nm)

    vbox1.addWidget(add1)
    fbox.addRow(l2, vbox1)

    vbox2.addWidget(add2)
    fbox.addRow(l3, vbox2)

    vbox3.addWidget(add3)
    fbox.addRow(l4, vbox3)


    
    fbox.addRow(QPushButton("Submeter"), QPushButton("Cancelar"))

    win.setLayout(fbox)

    win.setWindowTitle("PyQt")
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    window()
