# -*- coding: utf-8 -*-

import logging

from gi.repository import GObject, Gtk
from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory

from Config import Config
from Netsoul import NsProtocol
from MainWindow import MainWindow
from Systray import Systray

from SettingsWindow import SettingsWindow
from AddContactWindow import AddContactWindow
from ChatWindow import ChatWindow


class Manager(GObject.GObject, ClientFactory):
    __gsignals__ = {
        'reconnecting': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        'connecting': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        'disconnected': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        'connected': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        'logged': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        'login-failed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, []),
        'login': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
        'logout': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
        'msg': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT, GObject.TYPE_STRING, GObject.TYPE_PYOBJECT]),
        'who': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
        'state': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT, GObject.TYPE_STRING]),
        'is-typing': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
        'cancel-typing': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_PYOBJECT]),
        'contact-added': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_STRING]),
        'contact-deleted': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, [GObject.TYPE_STRING]),
    }
    _protocol = None
    _tryReconnecting = False
    _chatWindows = {}

    def __init__(self):
        GObject.GObject.__init__(self)
        self._mainwindow = MainWindow(self)
        self._systray = Systray(self, self._mainwindow)
        if Config['autoConnect']:
            self.doConnectSocket()

    # Senders

    def sendState(self, state):
        if self._protocol is not None:
            self._protocol.sendState(state)

    def sendWatch(self, sendWho=True):
        if self._protocol is not None:
            self._protocol.sendWatch(sendWho)

    def sendMsg(self, msg, dests):
        if self._protocol is not None:
            self._protocol.sendMsg(msg, dests)

    def sendWho(self, logins):
        if self._protocol is not None:
            self._protocol.sendWho(logins)

    def sendExit(self):
        if self._protocol is not None:
            self._protocol.sendExit()

    def sendStartTyping(self, dests):
        if self._protocol is not None:
            self._protocol.sendStartTyping(dests)

    def sendCancelTyping(self, dests):
        if self._protocol is not None:
            self._protocol.sendCancelTyping(dests)

    # Actions

    def doConnectSocket(self):
        if self._protocol is not None:
            self.doDisconnectSocket()
        self._tryReconnecting = True
        reactor.connectTCP("ns-server.epita.fr", 4242, self, timeout=10)

    def doDisconnectSocket(self):
        if self._protocol is not None:
            self._tryReconnecting = False
            self.sendExit()
            self._protocol.transport.loseConnection()
            self._protocol = None

    def doOpenChat(self, login):
        if login not in self._chatWindows:
            self._chatWindows[login] = ChatWindow(self, login, False)
        return self._chatWindows[login]

    def doDeleteContact(self, login):
        try:
            Config['watchlist'].remove(login)
        except ValueError:
            return False
        else:
            self.emit('contact-deleted', login)
            return True

    def doAddContact(self, login):
        if login and login not in Config['watchlist']:
            Config['watchlist'].add(login)
            self.emit('contact-added', login)
            return True
        return False

    # Events

    def connectEvent(self, *args, **kwargs):
        self.doConnectSocket()

    def disconnectEvent(self, *args, **kwargs):
        self.doDisconnectSocket()

    def quitEvent(self, *args, **kwargs):
        reactor.stop()

    def closeChatWindowEvent(self, widget, event, login):
        widget.destroy()
        if login in self._chatWindows:
            del self._chatWindows[login]
        return True

    def openAddContactWindowEvent(self, *args, **kwargs):
        win = AddContactWindow()
        if win.run() == Gtk.ResponseType.OK:
            login = win.getLogin()
            win.destroy()
            self.doAddContact(login)
        else:
            win.destroy()

    def openSettingsWindowEvent(self, *args, **kwargs):
        win = SettingsWindow()
        if win.run() == Gtk.ResponseType.APPLY:
            for key, value in win.getAllParams().iteritems():
                Config[key] = value
        win.destroy()

    # GSignals methods

    def do_logged(self):
        self.sendState('actif')
        self.sendWatch()

    def do_login_failed(self):
        self.doDisconnectSocket()

    def do_contact_added(self, login):
        self.sendWatch()

    def do_contact_deleted(self, login):
        self.sendWatch()

    def do_msg(self, info, msg, dests):
        if info.login not in self._chatWindows:
            win = self.doOpenChat(info.login)
            win.addMsg(msg)

    # NsProtocol Hooks

    def setProtocol(self, protocol):
        self._protocol = protocol

    def connectionMadeHook(self):
        logging.info('Manager : Connected')
        self.emit('connected')

    def loggedHook(self):
        logging.info('Manager : Logged successfully')
        self.emit('logged')

    def loginFailedHook(self):
        logging.info('Manager : Login failed')
        self.emit('login-failed')

    def cmdLoginHook(self, info):
        logging.info(u'Manager : Cmd %s login' % info)
        self.emit('login', info)

    def cmdLogoutHook(self, info):
        logging.info(u'Manager : Cmd %s logout' % info)
        self.emit('logout', info)

    def cmdMsgHook(self, info, msg, dests):
        logging.info(u'Manager : Cmd %s msg "%s" %s' % (info, msg, dests))
        self.emit('msg', info, msg, dests)

    def cmdWhoHook(self, result):
        logging.info(u'Manager : Who %s' % result)
        self.emit('who', result)

    def cmdStateHook(self, info, state):
        logging.info(u'Manager : Cmd %s state %s' % (info, state))
        self.emit('state', info, state)

    def cmdIsTypingHook(self, info):
        logging.info(u'Manager : Cmd %s is typing' % info)
        self.emit('is-typing', info)

    def cmdCancelTypingHook(self, info):
        logging.info(u'Manager : Cmd %s cancel typing' % info)
        self.emit('cancel-typing', info)

    # ClientFactory

    def buildProtocol(self, addr):
        return NsProtocol(self)

    def startedConnecting(self, connector):
        logging.info('Manager : Started connecting')
        self.emit('connecting')

    def clientConnectionFailed(self, connector, reason):
        self._protocol = None
        logging.warning('Manager : Connection failed reconnecting in 3 seconds')
        reactor.callLater(3, connector.connect)
        self.emit('reconnecting')

    def clientConnectionLost(self, connector, reason):
        self._protocol = None
        if self._tryReconnecting:
            logging.warning('Manager : Connection lost reconnecting in 3 seconds')
            reactor.callLater(3, connector.connect)
            self.emit('reconnecting')
        else:
            logging.info('Manager : Connection closed')
            self.emit('disconnected')