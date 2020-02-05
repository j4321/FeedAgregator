#! /usr/bin/python3
# -*- coding:Utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2018-2019 Juliette Monsel <j_4321@protonmail.com>

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


Desktop widget for a single feed
"""
import configparser
import pickle
from tkinter import BooleanVar
from tkinter.ttk import Entry

from feedagregatorlib.constants import CONFIG, FEEDS, add_trace, load_data, save_feeds
from feedagregatorlib.messagebox import askokcancel
from .base_widget import BaseWidget


class FeedWidget(BaseWidget):
    def __init__(self, master, feed_name):
        self.entries = []
        BaseWidget.__init__(self, master, feed_name, FEEDS, save_feeds)
        self.label.bind('<Double-1>', self.rename)

    def _create_menu(self):
        BaseWidget._create_menu(self)

        self._sort_is_reversed = BooleanVar(self,
                                            FEEDS.getboolean(self.name,
                                                             'sort_is_reversed',
                                                             fallback=False))
        add_trace(self._sort_is_reversed, 'write', self._sort_trace)

        self.menu_sort.add_radiobutton(label=_('Oldest first'),
                                       variable=self._sort_is_reversed,
                                       value=True,
                                       command=self.sort_by_date)
        self.menu_sort.add_radiobutton(label=_('Most recent first'),
                                       variable=self._sort_is_reversed,
                                       value=False,
                                       command=self.sort_by_date)
        self.menu.add_command(label=_('Remove feed'), command=self.remove_feed)

    def populate_widget(self):
        try:
            filename = FEEDS.get(self.name, 'data')
            latest, data = load_data(filename)
        except (configparser.NoOptionError, pickle.UnpicklingError):
            data = []
        for entry_title, date, summary, link in data:
            self.entry_add(entry_title, date, summary, link, -1)
        self.sort_by_date()

    def remove_feed(self):
        rep = True
        if CONFIG.getboolean('General', 'confirm_remove', fallback=True):
            rep = askokcancel(_('Confirmation'),
                              _('Do you want to remove the feed {feed}?').format(feed=self.name))
        if rep:
            self.master.feed_remove(self.name)

    def open_all(self):
        for tf, l, b in self.entries:
            tf.open()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def close_all(self):
        for tf, l, b in self.entries:
            tf.close()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def clear(self):
        for tf, l, b in self.entries:
            tf.destroy()
        self.entries.clear()

    def entry_add(self, title, date, summary, url, index=0):
        """Display entry."""
        tf, l, b = BaseWidget.entry_add(self, title, date, summary, url)
        if index == -1:
            self.entries.append((tf, l, b))
        else:
            self.entries.insert(index, (tf, l, b))

    def rename(self, event):

        def ok(event):
            name = entry.get()
            entry.destroy()
            if name:
                self.master.feed_rename(self.name, name)

        entry = Entry(self, justify='center')
        entry.insert(0, self.name)
        entry.selection_range(0, 'end')
        entry.place(in_=self.label, relwidth=1, relheight=1, x=0, y=0, anchor='nw')
        entry.bind('<Return>', ok)
        entry.bind('<Escape>', lambda e: entry.destroy())
        entry.bind('<FocusOut>', lambda e: entry.destroy())
        entry.focus_force()

    def rename_feed(self, new_name):
        self.name = new_name
        self.title('feedagregator.widget.{}'.format(new_name.replace(' ', '_')))
        self.label.configure(text=new_name)

    def update_style(self):
        BaseWidget.update_style(self)
        for tf, l, b in self.entries:
            l.set_style(self._stylesheet)
            l.set_font_size(self._font_size)

    def sort_by_date(self):
        if self._sort_is_reversed.get():
            l = reversed(self.entries)
        else:
            l = self.entries
        for i, (tf, l, b) in enumerate(l):
            tf.grid_configure(row=i)

    def _sort_trace(self, *args):
        FEEDS.set(self.name, 'sort_is_reversed', str(self._sort_is_reversed.get()))
        save_feeds()
