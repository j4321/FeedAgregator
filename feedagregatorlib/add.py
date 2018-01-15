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


Add feed dialog
"""
from tkinter import Toplevel
from tkinter.ttk import Label, Entry, Button, Frame
from feedagregatorlib.constants import APP_NAME


class Add(Toplevel):
    def __init__(self, master):
        Toplevel.__init__(self, master, class_=APP_NAME, padx=6, pady=6)
        self.title(_("Add Feed"))
        self.grab_set()
        self.resizable(True, False)
        self.columnconfigure(1, weight=1)

        Label(self, text=_('URL')).grid(row=0, column=0, sticky='e', pady=4, padx=4)
        self.url = ""
        self.url_entry = Entry(self, width=30)
        self.url_entry.grid(row=0, column=1, sticky='ew', pady=4, padx=4)
        self.url_entry.bind('<Return>', self.validate)
        frame = Frame(self)
        frame.grid(row=1, column=0, columnspan=2)
        Button(frame, text=_('Ok'), command=self.validate).grid(row=0, column=0,
                                                                sticky='e',
                                                                pady=4, padx=4)

        Button(frame, text=_('Cancel'), command=self.destroy).grid(row=0,
                                                                   column=1,
                                                                   sticky='w',
                                                                   pady=4,
                                                                   padx=4)
        self.url_entry.focus_set()

    def validate(self, event=None):
        self.url = self.url_entry.get().strip()
        self.destroy()
