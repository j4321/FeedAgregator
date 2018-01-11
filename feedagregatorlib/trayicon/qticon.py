#! /usr/bin/python3
# -*- coding:Utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2018 Juliette Monsel <j_4321@protonmail.com>

FeedAgregator is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

FeedAgregator is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


System tray icon using Qt.
"""

try:
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
    from PyQt5.QtGui import QIcon
except ImportError:
    try:
        from PyQt4.QtGui import QApplication, QSystemTrayIcon, QMenu, QAction, QIcon
    except ImportError:
        from PySide.QtGui import QApplication, QSystemTrayIcon, QMenu, QAction, QIcon
import sys


class SubMenu(QMenu):
    def __init__(self, *args, label=None, parent=None, **kwargs):
        if label is None:
            QMenu.__init__(self, parent)
        else:
            QMenu.__init__(self, label, parent)

    def add_separator(self):
        self.addSeparator()

    def add_command(self, label="", command=None):
        action = QAction(label, self)
        if command is not None:
            action.triggered.connect(lambda *args: command())
        self.addAction(action)

    def add_checkbutton(self, label="", command=None):
        action = QAction(label, self)
        action.setCheckable(True)
        if command is not None:
            action.triggered.connect(lambda *args: command())
        self.addAction(action)

    def add_cascade(self, label="", menu=None):
        if menu is None:
            menu = SubMenu(label, self)
        action = QAction(label, self)
        action.setMenu(menu)
        self.addAction(action)

    def delete(self, item1, item2=None):
        index1 = self.index(item1)
        if item2 is None:
            self.removeAction(self.actions()[index1])
        else:
            index2 = self.index(item2)
            a = self.actions()
            for i in range(index1, index2):
                self.removeAction(a[i])

    def index(self, index):
        if isinstance(index, int):
            return index
        elif index == "end":
            return len(self.actions())
        else:
            try:
                i = [i.text() for i in self.actions()].index(index)
            except ValueError:
                raise ValueError("%r not in menu" % index)
            return i

    def get_item_label(self, item):
        return self.actions()[self.index(item)].text()

    def set_item_label(self, item, label):
        i = self.actions()[self.index(item)]
        i.setText(label)

    def set_item_menu(self, item, menu):
        i = self.actions()[self.index(item)]
        i.setMenu(menu)

    def get_item_menu(self, item):
        i = self.actions()[self.index(item)]
        return i.menu()

    def disable_item(self, item):
        self.actions()[self.index(item)].setDisabled(True)

    def enable_item(self, item):
        self.actions()[self.index(item)].setDisabled(False)

    def get_item_value(self, item):
        """Return item value (True/False) if item is a checkbutton."""
        return self.actions()[self.index(item)].isChecked()

    def set_item_value(self, item, value):
        """Set item value if item is a checkbutton."""
        i = self.actions()[self.index(item)]
        i.setChecked(value)


class TrayIcon(QApplication):

    def __init__(self, icon, **kwargs):
        QApplication.__init__(self, sys.argv)
        self._icon = QIcon(icon)
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(self._icon)

        self.menu = SubMenu()
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def loop(self, tk_window):
        self.processEvents()
        tk_window.loop_id = tk_window.after(10, self.loop, tk_window)

    def change_icon(self, icon, desc):
        del self._icon
        self._icon = QIcon(icon)
        self.tray_icon.setIcon(self._icon)

    def bind_left_click(self, command):

        def action(reason):
            """Execute command only on click (not when the menu is displayed)."""
            if reason == QSystemTrayIcon.Trigger:
                command()

        self.tray_icon.activated.connect(action)
