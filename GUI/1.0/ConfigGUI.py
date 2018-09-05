import sys
import glob
import serial
import serial.tools.list_ports
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
    add3.addItems(serial_ports())
    print(serial_ports())
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


def serial_ports():
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
    return result


if __name__ == '__main__':
    window()
