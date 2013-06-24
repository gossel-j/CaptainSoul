# -*- coding: utf-8 -*-

import gtk

from captainsoul.common import CptCommon
from captainsoul import Icons


class Buddy(object):
    def __init__(self, no, login, state, ip, location):
        self._no, self._login, self._state, self._ip, self._location = int(no), login, state, ip, location

    @property
    def no(self):
        return self._no

    @property
    def login(self):
        return self._login

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def ip(self):
        return self._ip

    @property
    def location(self):
        return self._location

    def atSchool(self):
        return self._ip.startswith('10.')

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '<Buddy %d %s %s %s "%s">' % (self.no, self.login, self.state, self.ip, self.location)


class LoginList(CptCommon):
    def __init__(self):
        self._list = {}

    def clean(self):
        self._list = {no: buddy for no, buddy in self._list.iteritems() if buddy.login in self.config['watchlist']}

    def processWho(self, results):
        self._list = {no: b for no, b in self._list.iteritems() if b.login not in results.logins}
        for r in results:
            if r.login in self.config['watchlist']:
                self._list[r.no] = Buddy(r.no, r.login, r.state, r.ip, r.location)

    def formatWatchList(self):
        return [(self.getState(login), login, self.atSchool(login)) for login in self.config['watchlist']]

    def getFromLogin(self, login):
        return [buddy for buddy in self._list.itervalues() if buddy.login == login]

    def getState(self, login):
        state = 'logout'
        for buddy in self.getFromLogin(login):
            if state == 'logout' and buddy.state in ('away', 'lock', 'actif') or state in ('away', 'lock') and buddy.state == 'actif':
                state = buddy.state
        return state

    def atSchool(self, login):
        return any([buddy.atSchool() for buddy in self.getFromLogin(login)])

    def changeState(self, info, state):
        if info.login in self.config['watchlist']:
            if info.no in self._list:
                self._list[info.no].state = state
            else:
                self._list[info.no] = Buddy(info.no, info.login, state, info.ip, info.location)

    def logout(self, info):
        if info.no in self._list:
            del self._list[info.no]


class WatchList(gtk.TreeView, CptCommon):
    _loginColumn = 1

    def __init__(self):
        super(WatchList, self).__init__(model=gtk.ListStore(gtk.gdk.Pixbuf, str, gtk.gdk.Pixbuf, str))
        self._list = LoginList()
        self.set_rules_hint(True)
        self._listStore.set_sort_column_id(self._loginColumn, gtk.SORT_ASCENDING)
        columns = [
            gtk.TreeViewColumn("State", gtk.CellRendererPixbuf(), pixbuf=0),
            gtk.TreeViewColumn("Login", gtk.CellRendererText(), text=self._loginColumn),
            gtk.TreeViewColumn("At school", gtk.CellRendererPixbuf(), pixbuf=2),
            gtk.TreeViewColumn("", gtk.CellRendererText(), text=3)
        ]
        for column in columns:
            self.append_column(column)
        self.connect("row-activated", self.rowActivated)
        self.connect("button-press-event", self.buttonPressEvent)
        self.connect('show', self.showEvent)
        self.manager.connect('state', self.stateEvent)
        self.manager.connect('contact-added', self.contactAddedEvent)
        self.manager.connect('contact-deleted', self.contactDeletedEvent)
        self.manager.connect('who', self.whoEvent)
        self.manager.connect('logout', self.logoutEvent)
        self.refreshStore()

    @property
    def _listStore(self):
        return self.get_model()

    def refreshStore(self):
        self._listStore.clear()
        pixs = {
            'actif': Icons.green.get_pixbuf(),
            'away': Icons.orange.get_pixbuf(),
            'lock': Icons.red.get_pixbuf()
        }
        for state, login, atSchool in self._list.formatWatchList():
            self._listStore.append([
                pixs.get(state, Icons.void.get_pixbuf()),
                login,
                Icons.epitech.get_pixbuf() if atSchool else Icons.void.get_pixbuf(),
                "",
            ])

    def stateEvent(self, widget, info, state):
        self._list.changeState(info, state)
        self.refreshStore()

    def contactAddedEvent(self, widget, login):
        self._list.clean()
        self.refreshStore()

    def contactDeletedEvent(self, widget, login):
        self._list.clean()
        self.refreshStore()

    def rowActivated(self, tv, path, column):
        self.manager.doOpenChat(self._listStore.get_value(self._listStore.get_iter(path), self._loginColumn))

    def buttonPressEvent(self, wid, event):
        # 3 is right click
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            path = self.get_path_at_pos(int(event.x), int(event.y))
            if path is not None:
                login = self._listStore.get_value(self._listStore.get_iter(path[0]), self._loginColumn)
                menu = gtk.Menu()
                items = [
                    (gtk.STOCK_DELETE, 'Delete', self.deleteContactEvent),
                    (gtk.STOCK_FILE, 'Send file', self.sendFileEvent)
                ]
                for stock, label, call in items:
                    item = gtk.ImageMenuItem(stock_id=stock)
                    item.set_label(label)
                    item.connect("activate", call, login)
                    item.show()
                    menu.append(item)
                menu.popup(None, None, None, event.button, event.time)

    def showEvent(self, widget):
        self.grab_focus()

    def deleteContactEvent(self, widget, login):
        self.manager.doDeleteContact(login)

    def sendFileEvent(self, widget, login):
        self.downloadManager.startFileUpload(login)

    def whoEvent(self, widget, results):
        self._list.processWho(results)
        self.refreshStore()

    def logoutEvent(self, widget, info):
        self._list.logout(info)
        self.refreshStore()