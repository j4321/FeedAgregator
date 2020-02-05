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


Desktop category widget
"""
import configparser
import pickle
from datetime import datetime
from locale import getlocale
from tkinter import StringVar, TclError
from webbrowser import open as webopen

from babel.dates import format_datetime

from feedagregatorlib.constants import CONFIG, FEEDS, LATESTS, add_trace, \
    feed_get_latest, save_latests, load_data
from feedagregatorlib.messagebox import askokcancel
from .base_widget import BaseWidget


class CatWidget(BaseWidget):
    def __init__(self, master, category):
        self.entries = {}

        BaseWidget.__init__(self, master, category, LATESTS, save_latests)

        # --- elements
        title = _('Feeds: Latests') if category == 'All' else _('Feeds: {category}').format(category=category)
        self.label.configure(text=title)

    def _create_menu(self):
        BaseWidget._create_menu(self)

        self._sort_order = StringVar(self, LATESTS.get(self.name, 'sort_order', fallback='A-Z'))
        add_trace(self._sort_order, 'write', self._order_trace)
        self.menu_sort.add_radiobutton(label='A-Z',
                                       variable=self._sort_order, value='A-Z',
                                       command=lambda: self._sort_by_name(reverse=False))
        self.menu_sort.add_radiobutton(label='Z-A',
                                       variable=self._sort_order, value='Z-A',
                                       command=lambda: self._sort_by_name(reverse=True))
        self.menu_sort.add_radiobutton(label=_('Oldest first'),
                                       variable=self._sort_order, value='oldest',
                                       command=lambda: self._sort_by_date(reverse=False))
        self.menu_sort.add_radiobutton(label=_('Most recent first'),
                                       variable=self._sort_order, value='latest',
                                       command=lambda: self._sort_by_date(reverse=True))
        if self.name != 'All':
            self.menu.add_command(label=_('Remove category'), command=self.remove_cat)

    def populate_widget(self):
        for tf, l, b in self.entries.values():
            tf.destroy()
        self.entries.clear()
        for title in sorted(FEEDS.sections(), key=lambda x: x.lower()):
            if self.name in ['All', FEEDS.get(title, 'category', fallback='')]:
                try:
                    filename = FEEDS.get(title, 'data')
                    latest_data = feed_get_latest(filename)
                except (configparser.NoOptionError, pickle.UnpicklingError):
                    latest = ''
                    url = FEEDS.get(title, 'url')
                else:
                    try:
                        latest, url = latest_data
                    except ValueError:  # old data
                        latest, data = load_data(filename)
                        url = data[0][-1]
                date = FEEDS.get(title, 'updated')
                self.entry_add(title, date, latest, url)
        self.sort()

    def remove_cat(self):
        rep = True
        if CONFIG.getboolean('General', 'confirm_cat_remove', fallback=True):
            rep = askokcancel(_('Confirmation'),
                              _('Do you want to remove the category {category}?').format(category=self.name))
        if rep:
            for title in self.entries:
                FEEDS.set(title, 'category', '')
            self.master.category_remove(self.name)

    def open_all(self):
        for tf, l, b in self.entries.values():
            tf.open()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def close_all(self):
        for tf, l, b in self.entries.values():
            tf.close()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def entry_add(self, title, date, summary, url):
        """Display feed."""
        self.entries[title] = BaseWidget.entry_add(self, title, date, summary, url)

    def hide_feed(self, title):
        self.entries[title][0].grid_remove()

    def show_feed(self, title):
        self.entries[title][0].grid()

    def remove_feed(self, title):
        self.entries[title][0].destroy()
        del self.entries[title]

    def rename_feed(self, old_name, new_name):
        self.entries[new_name] = self.entries.pop(old_name)
        old_title = self.entries[new_name][0].label.cget('text')
        self.entries[new_name][0].label.configure(text=old_title.replace(old_name, new_name))

    def update_display(self, title, latest, date, link):
        formatted_date = format_datetime(datetime.strptime(date, '%Y-%m-%d %H:%M').astimezone(tz=None),
                                         'short', locale=getlocale()[0])
        tf, l, b = self.entries[title]
        tf.label.configure(text="{} - {}".format(title, formatted_date))
        l.set_content(latest)
        l.set_style(self._stylesheet)
        l.update_idletasks()
        b.configure(command=lambda: webopen(link))
        if tf.winfo_ismapped():
            try:
                l.configure(height=l.html.bbox()[-1])
            except TclError:
                self.after(10, self._on_configure, None)

    def update_style(self):
        BaseWidget.update_style(self)
        for tf, l, b in self.entries.values():
            l.set_style(self._stylesheet)
            l.set_font_size(self._font_size)

    def _sort_by_name(self, reverse):
        titles = sorted(self.entries, reverse=reverse, key=lambda x: x.lower())
        for i, title in enumerate(titles):
            self.entries[title][0].grid_configure(row=i)

    def sort(self):
        order = self._sort_order.get()
        if order == 'A-Z':
            self._sort_by_name(False)
        elif order == 'Z-A':
            self._sort_by_name(True)
        elif order == 'oldest':
            self._sort_by_date(False)
        else:
            self._sort_by_date(True)

    def _order_trace(self, *args):
        LATESTS.set(self.name, 'sort_order', self._sort_order.get())
        save_latests()

    def _sort_by_date(self, reverse):
        titles = sorted(self.entries, reverse=reverse, key=lambda x: FEEDS.get(x, 'updated'))
        for i, title in enumerate(titles):
            self.entries[title][0].grid_configure(row=i)
