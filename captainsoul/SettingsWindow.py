# -*- coding: utf-8 -*-

import gtk

from Config import Config
import Icons


class SettingsWindow(gtk.Dialog):
    def __init__(self):
        super(SettingsWindow, self).__init__(title="CaptainSoul - Settings")
        self.set_properties(resizable=False, icon=Icons.shield.get_pixbuf())
        self._createUi()
        self.show_all()

    def getAllParams(self):
        return {
            'login': self._entries['login'].get_text(),
            'password': self._entries['password'].get_text(),
            'location': self._entries['location'].get_text(),
            'autoConnect': self._autoButton.get_active()
        }

    def _createUi(self):
        # create entries
        self._entries = {key: gtk.Entry() for key in ['login', 'password', 'location']}
        for key, entry in self._entries.iteritems():
            entry.set_text(Config[key])
        self._entries['password'].set_visibility(False)
        # create table and populate it
        table = gtk.Table(4, 3, True)
        # login
        table.attach(gtk.Label("Login:"), 0, 1, 0, 1)
        table.attach(self._entries['login'], 1, 3, 0, 1)
        # password
        table.attach(gtk.Label("Password:"), 0, 1, 1, 2)
        table.attach(self._entries['password'], 1, 3, 1, 2)
        # location
        table.attach(gtk.Label("Location:"), 0, 1, 2, 3)
        table.attach(self._entries['location'], 1, 3, 2, 3)
        # autoConnect
        table.attach(gtk.Label("Auto-connect:"), 0, 2, 3, 4)
        self._autoButton = gtk.CheckButton()
        self._autoButton.set_active(Config['autoConnect'])
        table.attach(self._autoButton, 2, 3, 3, 4)
        self.vbox.pack_start(table, True, True, 0)
        self.add_buttons("Apply", gtk.RESPONSE_APPLY, "Cancel", gtk.RESPONSE_CANCEL)
