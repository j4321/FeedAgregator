#! /usr/bin/python3
# -*- coding:Utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2016-2017 Juliette Monsel <j_4321@protonmail.com>

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


Check for updates
"""


import os
try:
    from subprocess import run
except ImportError:
    from subprocess import call as run
from threading import Thread
from webbrowser import open as webOpen
from tkinter import Toplevel
from tkinter.ttk import Label, Button, Frame, Checkbutton
from feedagregatorlib.constants import CONFIG, save_config, IM_QUESTION_DATA, \
    IM_ICON_SVG, APP_NAME, PhotoImage
from feedagregatorlib.version import __version__
import feedparser


class UpdateChecker(Toplevel):

    def __init__(self, master, notify=False):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.title(_("Update"))
        self.withdraw()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.quit)

        self.notify = notify
        self._version = __version__

        self.img = PhotoImage(data=IM_QUESTION_DATA, master=self)

        frame = Frame(self)
        frame.grid(row=0, columnspan=2, sticky="ewsn")
        Label(frame, image=self.img).pack(side="left", padx=(10, 4), pady=(10, 4))
        Label(frame,
              text=_("A new version of {app_name} is available.\
\nDo you want to download it?").format(app_name=APP_NAME),
              font="TkDefaultFont 10 bold",
              wraplength=335).pack(side="left", padx=(4, 10), pady=(10, 4))

        self.b1 = Button(self, text=_("Yes"), command=self.download)
        self.b1.grid(row=1, column=0, padx=10, pady=10, sticky="e")
        Button(self, text=_("No"), command=self.quit).grid(row=1, column=1,
                                                           padx=10, pady=10,
                                                           sticky="w")
        self.ch = Checkbutton(self, text=_("Check for updates on startup."))
        if CONFIG.getboolean("General", "check_update"):
            self.ch.state(("selected", ))
        self.ch.grid(row=2, columnspan=2, sticky='w')
        self.update = None

        self.thread = Thread(target=self.update_available, daemon=True)
        self.thread.start()
        self.after(1000, self.check_update)

    def check_update(self):
        if self.update is None:
            self.after(1000, self.check_update)
        elif self.update:
            self.deiconify()
            self.grab_set()
            self.lift()
            self.b1.focus_set()
        else:
            if self.notify:
                run(["notify-send", "-i", IM_ICON_SVG, _("Update"),
                     _("{app_name} is up-to-date.").format(app_name=APP_NAME)])
            self.destroy()

    def quit(self):
        CONFIG.set("General", "check_update", str("selected" in self.ch.state()))
        save_config()
        self.destroy()

    def download(self):
        webOpen("https://github.com/j4321/{app_name}/releases/tag/v{version}".format(app_name=APP_NAME,
                                                                                     version=self._version))
        self.quit()

    def update_available(self):
        """
        Check for updates online, return True if an update is available, False
        otherwise (and if there is no Internet connection).
        """
        feed = feedparser.parse("https://github.com/j4321/{app_name}/releases.atom".format(app_name=APP_NAME))
        try:
            # feed['entries'][0]['id'] is of the form 'tag:github.com,...:Repository/.../vx.y.z'
            self._version = os.path.split(feed['entries'][0]['id'])[1][1:]
            self.update = self._version
        except IndexError:
            # feed['entries'] == [] because there is no Internet connection
            self.update = False
