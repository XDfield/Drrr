# -*- coding: utf-8 -*-
# Created by DoSun on 2017/5/20
import sys
import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from PyQt5.uic import *
from drrr_window import *
from connect_window import *
from create_window import *

__version__ = '1.0'
MAX_LENGTH = 140
# SIZEOF_UINT16 = 2

UiFile = 'drrr_window.ui'


# Ui_Drrr, QtBaseClass = loadUiType(UiFile)


class ShadowWindow(QWidget):
    """构造有底部阴影的窗口类"""

    def __init__(self):
        super(ShadowWindow, self).__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.SHADOW_WIDTH = 15

    def drawShadow(self, painter):
        painter.drawPixmap(0,
                           0,
                           self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/left_top.png'))
        painter.drawPixmap(self.width() - self.SHADOW_WIDTH,
                           0,
                           self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/right_top.png'))
        painter.drawPixmap(0,
                           self.height() - self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/left_bottom.png'))
        painter.drawPixmap(self.width() - self.SHADOW_WIDTH,
                           self.height() - self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/right_bottom.png'))
        painter.drawPixmap(0,
                           self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           self.height() - 2 * self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/left_mid.png').scaled(self.SHADOW_WIDTH,
                                                                       self.height() - 2 * self.SHADOW_WIDTH))
        painter.drawPixmap(self.width() - self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           self.height() - 2 * self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/right_mid.png').scaled(self.SHADOW_WIDTH,
                                                                        self.height() - 2 * self.SHADOW_WIDTH))
        painter.drawPixmap(self.SHADOW_WIDTH,
                           0,
                           self.width() - 2 * self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/top_mid.png').scaled(self.width() - 2 * self.SHADOW_WIDTH,
                                                                      self.SHADOW_WIDTH))
        painter.drawPixmap(self.SHADOW_WIDTH,
                           self.height() - self.SHADOW_WIDTH,
                           self.width() - 2 * self.SHADOW_WIDTH,
                           self.SHADOW_WIDTH,
                           QPixmap(':/shadow/img/bottom_mid.png').scaled(self.width() - 2 * self.SHADOW_WIDTH,
                                                                         self.SHADOW_WIDTH))

    def paintEvent(self, event):
        painter = QPainter(self)
        self.drawShadow(painter)
        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.white)


class Backend(QThread):
    """单独线程刷新时间显示"""
    updateDate = pyqtSignal(str)

    def run(self):
        while True:
            dateNow = QDate.currentDate().toString('MM/dd')
            timeNow = QTime.currentTime().toString('hh:mm')
            dateTime = dateNow + ' ' + timeNow
            self.updateDate.emit(dateTime)
            time.sleep(1)


class connectServer(QDialog, ShadowWindow, Ui_connectDialog):
    """连接服务器对话框"""

    def __init__(self):
        super(connectServer, self).__init__()
        self.setupUi(self)


class createServer(QDialog, ShadowWindow, Ui_createDialog):
    """创建服务器对话框"""

    def __init__(self):
        super(createServer, self).__init__()
        self.setupUi(self)


class TcpClientSocket(QTcpSocket):
    updateClient = pyqtSignal(str)

    def __init__(self, parent=None):
        super(TcpClientSocket, self).__init__(parent)
        self.readyRead.connect(self.dataReceive)
        self.disconnected.connect(self.slotDisconnected)

    def dataReceive(self):
        stream = QDataStream(self)
        stream.setVersion(QDataStream.Qt_5_6)
        while self.bytesAvailable() > 0:
            msg = stream.readQString()
            self.updateClient.emit(msg)

    def slotDisconnected(self):
        pass


class TcpServer(QTcpServer):
    """创建服务器"""
    updateServer = pyqtSignal(str)

    def __init__(self, parent=None):
        super(TcpServer, self).__init__(parent)
        self.tcpClientSocketList = []
        self.request = None

    def incomingConnection(self, socketId):
        tcpClientSocket = TcpClientSocket(self)
        tcpClientSocket.updateClient[str].connect(self.updateClients)
        tcpClientSocket.disconnected.connect(self.slotDisconnected)
        tcpClientSocket.setSocketDescriptor(socketId)
        self.tcpClientSocketList.append(tcpClientSocket)

    def updateClients(self, msg):
        self.updateServer.emit(msg)
        for i in range(len(self.tcpClientSocketList)):
            item = self.tcpClientSocketList[i]
            self.request = QByteArray()
            stream = QDataStream(self.request, QIODevice.WriteOnly)
            stream.setVersion(QDataStream.Qt_5_6)
            stream.writeQString(msg)
            item.write(self.request)
            self.request = None

    def slotDisconnected(self, socketId):
        for i in range(len(self.tcpClientSocketList)):
            item = self.tcpClientSocketList[i]
            if item.socketDescriptor() == socketId:
                self.tcpClientSocketList.remove(i)
                return
            return


class DrrrMainWindow(Ui_Drrr, ShadowWindow):
    """主窗口"""
    updateClients = pyqtSignal(str)

    def __init__(self):
        """主窗口的各项参数初始化"""
        super(DrrrMainWindow, self).__init__()
        self.setupUi(self)
        self.__leftButtonPress = False
        self.__movePoint = QPoint()
        self.tooMany = False

        self.today = QDate()

        self.textEdit.installEventFilter(self)
        self.textEdit.setTabChangesFocus(True)
        self.textEdit.document().setMaximumBlockCount(2)
        self.textEdit.textChanged.connect(self.maxLength)

        # html_pattern = '''
        # <html><head></head>
        # <body style='color:green'>
        # </body>
        # </html>
        # '''
        # self.textBrowser.setHtml(html_pattern)

        self.request = None
        self.isClient = False
        self.isServer = False

        self.postBtn.setEnabled(False)

        self.Binding()

    def maxLength(self):
        """判断输入文本字数长度是否超过限制"""
        text = self.textEdit.toPlainText()
        length = len(text)
        self.limit.setText(str(length) + r'/' + str(MAX_LENGTH))
        if length > MAX_LENGTH:
            self.tooMany = True
        else:
            self.tooMany = False

    def eventFilter(self, watch, event):
        """重构textEdit的按键监测 实现enter发送 ctrl+enter换行"""
        if watch == self.textEdit:
            if event.type() == QEvent.KeyPress:
                keyEvent = QKeyEvent(event)
                if keyEvent.key() == Qt.Key_Return:
                    if keyEvent.modifiers() & Qt.ControlModifier:
                        self.textEdit.append('')
                        return True
                    self.postMsg()
                    return True
                elif keyEvent.key() == Qt.Key_Enter:
                    self.postMsg()
                    return True
        return ShadowWindow.eventFilter(self, watch, event)

    def Binding(self):
        """按钮菜单等各项绑定"""
        self.MenuBinding()
        self.enterBtn.clicked.connect(self.postName)
        self.postBtn.clicked.connect(self.postMsg)

    def MenuBinding(self):
        """菜单设置"""
        settingMenu = QMenu(self)
        connectBtn = QAction('连接到服务器', self)
        createBtn = QAction('创建服务器', self)
        settingMenu.addActions([connectBtn, createBtn])
        self.settingBtn.setMenu(settingMenu)
        connectBtn.triggered.connect(self.connectServer)
        createBtn.triggered.connect(self.createServer)

    def connectServer(self):
        """服务器连接与断开选项"""
        if self.isServer:
            return
        if not self.isClient:  # 未连接到服务器则弹出连接对话框
            dialog = connectServer()
            self.socket = QTcpSocket()
            self.serverIP = QHostAddress()
            if dialog.exec_():
                ip = dialog.ipEdit.text()
                self.serverIP.setAddress(ip)
                port = int(dialog.portEdit.text())
                self.socket.connectToHost(self.serverIP.toString(), port)
            dialog.destroy()
            self.socket.connected.connect(self.slotConnected)
            self.socket.disconnected.connect(self.slotDisconnected)
            self.socket.readyRead.connect(self.dataReceived)
            self.isClient = True
            # 这里应该按情况修改菜单名称
        else:  # 再点一次则断开服务器
            msg = self.usernameLabel.text() + ' leave chat room.'
            self.sendMsg(msg)
            self.socket.disconnectFromHost()
            self.isClient = False

    def createServer(self):
        """服务器创建选项"""
        if self.isClient:
            return
        if not self.isServer:
            dialog = createServer()
            self.server = TcpServer(self)
            if dialog.exec_():
                port = int(dialog.portEdit.text())
                self.server.listen(QHostAddress.Any, port)
            dialog.destroy()
            self.server.updateServer[str].connect(self.updateBrowser)
            self.updateClients[str].connect(self.server.updateClients)
            self.isServer = True
            self.ipInfo.setText('Server Created')
            self.postBtn.setEnabled(True)
        else:
            self.server.close()
            self.isServer = False
            self.ipInfo.setText('Disconnected')
            self.postBtn.setEnabled(False)

    def updateBrowser(self, msg):
        """更新对话浏览器"""
        self.textBrowser.append(msg)

    def slotConnected(self):
        """服务器连接建立"""
        self.postBtn.setEnabled(True)
        msg = self.usernameLabel.text() + ' enter chat room.'
        self.sendMsg(msg)
        self.ipInfo.setText('Connected to:' + self.serverIP.toString())
        self.postBtn.setEnabled(True)

    def slotDisconnected(self):
        """断开连接"""
        self.postBtn.setEnabled(False)
        self.isClient = False
        self.ipInfo.setText('Disconnected')

    def dataReceived(self):
        """接受消息"""
        stream = QDataStream(self.socket)
        stream.setVersion(QDataStream.Qt_5_6)
        while self.socket.bytesAvailable() > 0:
            msg = stream.readQString()
            self.textBrowser.append(msg)

    def sendMsg(self, msg):
        """发送文本"""
        self.request = QByteArray()
        stream = QDataStream(self.request, QIODevice.WriteOnly)
        stream.setVersion(QDataStream.Qt_5_6)
        stream.writeQString(msg)
        self.socket.write(self.request)
        self.request = None

    def postName(self):
        """登陆后传递用户名"""
        self.Info.clear()
        if not self.usernameEdit.text():
            self.Info.setText('请输入用户名.')
        else:
            self.usernameLabel.setText(self.usernameEdit.text())
            self.centerStackedWidget.setCurrentIndex(1)
            self.textEdit.setFocus()

    def setDate(self, dateTime):
        """设定日期显示"""
        self.timeLabel.setText(dateTime)

    def postMsg(self):
        """发送文本"""
        self.Info.clear()
        if not (self.isClient or self.isServer):
            self.Info.setText('请先连接或创建服务器.')
            return
        if not self.textEdit.toPlainText():
            self.Info.setText('输入不能为空.')
            return
        if self.tooMany:
            self.Info.setText('每条信息最多' + str(MAX_LENGTH) + '个字符.')
            return
        Msg = self.usernameLabel.text() + ': ' + self.textEdit.toPlainText()
        self.textEdit.clear()
        if self.isServer:
            self.updateClients.emit(Msg)
            return
        # 发送文本给服务器
        self.sendMsg(Msg)

    # 重构鼠标点击拖动事件 实现窗口拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.titleBar.rect().contains(event.pos()):
                self.__leftButtonPress = True
                self.__movePoint = event.pos()

    def mouseMoveEvent(self, event):
        if self.__leftButtonPress:
            globalPos = event.globalPos()
            self.move(globalPos - self.__movePoint)

    def mouseReleaseEvent(self, event):
        self.__leftButtonPress = False

    def maxAndNormal(self):
        """最大化/正常化窗口按钮设置"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    drrr = DrrrMainWindow()
    backend = Backend()
    backend.updateDate.connect(drrr.setDate)
    backend.start()
    drrr.show()
    app.exec_()
