#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2018-2019 Juliette Monsel <j_4321@protonmail.com>
based on code by RedFantom Copyright (C) 2017
<https://github.com/RedFantom/ttkwidgets/blob/master/ttkwidgets/frames/toggledframe.py>

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


ToggledFrame class.
"""
from tkinter.ttk import Frame, Checkbutton, Style, Label


class ToggledFrame(Frame):
    """
    A frame that can be toggled to open and close
    """

    def __init__(self, master=None, text="", **kwargs):
        font = kwargs.pop('font', '')
        Frame.__init__(self, master, **kwargs)
        self.style_name = self.cget('style')
        self.toggle_style_name = '%s.Toggle' % ('.'.join(self.style_name.split('.')[:-1]))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self.style = Style(self)
        self.style.configure(self.toggle_style_name,
                             background=self.style.lookup(self.style_name, 'background'))
        self.style.map(self.toggle_style_name, background=[])
        self._checkbutton = Checkbutton(self,
                                        style=self.toggle_style_name,
                                        command=self.toggle,
                                        cursor='arrow')
        self.label = Label(self, text=text, font=font,
                           style=self.style_name.replace('TFrame', 'TLabel'))
        self.interior = Frame(self, style=self.style_name)
        self.interior.grid(row=1, column=1, sticky="nswe", padx=(4, 0))
        self.interior.grid_remove()
        self.label.bind('<Configure>', self._wrap)
        self.label.bind('<1>', lambda e: self._checkbutton.invoke())
        self._grid_widgets()
        self.bind('<<ThemeChanged>>', self._theme_changed)

    def _theme_changed(self, event):
        self.style.configure(self.toggle_style_name,
                             background=self.style.lookup(self.style_name, 'background'))

    def _wrap(self, event):
        self.label.configure(wraplength=self.label.winfo_width())

    def _grid_widgets(self):
        self._checkbutton.grid(row=0, column=0)
        self.label.grid(row=0, column=1, sticky="we")

    def toggle(self):
        if 'selected' not in self._checkbutton.state():
            self.interior.grid_remove()
            self.event_generate("<<ToggledFrameClose>>")
        else:
            self.interior.grid()
            self.event_generate("<<ToggledFrameOpen>>")

    def open(self):
        self._checkbutton.state(('selected',))
        self.interior.grid()
        self.event_generate("<<ToggledFrameOpen>>")

    def close(self):
        self._checkbutton.state(('!selected',))
        self.interior.grid_remove()
        self.event_generate("<<ToggledFrameClose>>")
