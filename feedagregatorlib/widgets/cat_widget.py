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
from datetime import datetime
from locale import getlocale
from tkinter import StringVar, TclError
from tkinter.ttk import Button
from webbrowser import open as webopen
import configparser
import pickle

from babel.dates import format_datetime

from feedagregatorlib.constants import CONFIG, FEEDS, add_trace, \
    LATESTS, feed_get_latest, save_latests
from feedagregatorlib.messagebox import askokcancel
from feedagregatorlib.tkinterhtml import HtmlFrame
from feedagregatorlib.toggledframe import ToggledFrame
from .base_widget import BaseWidget


class CatWidget(BaseWidget):
    def __init__(self, master, category):
        self.feeds = {}

        BaseWidget.__init__(self, master, category, LATESTS, save_latests)

        # --- elements
        title = _('Feeds: Latests') if category == 'All' else _('Feeds: {category}').format(category=category)
        self.label.configure(text=title)

        self.init_feed_display()

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

    def remove_cat(self):
        rep = True
        if CONFIG.getboolean('General', 'confirm_cat_remove', fallback=True):
            rep = askokcancel(_('Confirmation'),
                              _('Do you want to remove the category {category}?').format(category=self.name))
        if rep:
            for title in self.feeds:
                FEEDS.set(title, 'category', '')
            self.master.category_remove(self.name)

    def open_all(self):
        for tf, l in self.feeds.values():
            tf.open()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def close_all(self):
        for tf, l in self.feeds.values():
            tf.close()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def init_feed_display(self):
        for tf, l in self.feeds.values():
            tf.destroy()
        self.feeds.clear()
        for title in sorted(FEEDS.sections(), key=lambda x: x.lower()):
            if self.name in ['All', FEEDS.get(title, 'category', fallback='')]:
                try:
                    filename = FEEDS.get(title, 'data')
                    latest = feed_get_latest(filename)
                except (configparser.NoOptionError, pickle.UnpicklingError):
                    latest = ''
                url = FEEDS.get(title, 'url')
                date = FEEDS.get(title, 'updated')
                self.add_feed(title, latest, url, date)
        self.sort()

    def add_feed(self, title, latest, url, date):
        """Display feed."""

        def unwrap(event):
            l.update_idletasks()
            try:
                h = l.html.bbox()[-1]
            except TclError:
                pass
            else:
                l.configure(height=h + 2)

        def resize(event):
            if l.winfo_viewable():
                try:
                    h = l.html.bbox()[-1]
                except TclError:
                    pass
                else:
                    l.configure(height=h + 2)
        # convert date to locale time
        formatted_date = format_datetime(datetime.strptime(date, '%Y-%m-%d %H:%M').astimezone(tz=None),
                                         'short', locale=getlocale()[0])

        tf = ToggledFrame(self.display, text="{} - {}".format(title, formatted_date),
                          style='widget.TFrame')
        l = HtmlFrame(tf.interior, height=50, style='widget.interior.TFrame')
        l.set_content(latest)
        l.set_style(self._stylesheet)
        l.set_font_size(self._font_size)
        tf.interior.configure(style='widget.interior.TFrame')
        tf.interior.rowconfigure(0, weight=1)
        tf.interior.columnconfigure(0, weight=1)
        l.grid(padx=4, sticky='eswn')
        Button(tf.interior, text='Open', style='widget.TButton',
               command=lambda: webopen(url)).grid(pady=4, padx=6, sticky='e')
        tf.grid(sticky='we', row=len(self.feeds), pady=2, padx=(8, 4))
        tf.bind("<<ToggledFrameOpen>>", unwrap)
        l.bind("<Configure>", resize)
        self.feeds[title] = tf, l

    def hide_feed(self, title):
        self.feeds[title][0].grid_remove()

    def show_feed(self, title):
        self.feeds[title][0].grid()

    def remove_feed(self, title):
        self.feeds[title][0].destroy()
        del self.feeds[title]

    def rename_feed(self, old_name, new_name):
        self.feeds[new_name] = self.feeds.pop(old_name)
        old_title = self.feeds[new_name][0].label.cget('text')
        self.feeds[new_name][0].label.configure(text=old_title.replace(old_name, new_name))

    def update_display(self, title, latest, date):
        formatted_date = format_datetime(datetime.strptime(date, '%Y-%m-%d %H:%M').astimezone(tz=None),
                                         'short', locale=getlocale()[0])
        tf, l = self.feeds[title]
        tf.label.configure(text="{} - {}".format(title, formatted_date))
        l.set_content(latest)
        l.set_style(self._stylesheet)
        l.update_idletasks()
        if tf.winfo_ismapped():
            try:
                l.configure(height=l.html.bbox()[-1])
            except TclError:
                self.after(10, self._on_configure, None)

    def update_style(self):
        BaseWidget.update_style(self)
        for tf, l in self.feeds.values():
            l.set_style(self._stylesheet)
            l.set_font_size(self._font_size)

    def _sort_by_name(self, reverse):
        titles = sorted(self.feeds, reverse=reverse, key=lambda x: x.lower())
        for i, title in enumerate(titles):
            self.feeds[title][0].grid_configure(row=i)

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
        titles = sorted(self.feeds, reverse=reverse, key=lambda x: FEEDS.get(x, 'updated'))
        for i, title in enumerate(titles):
            self.feeds[title][0].grid_configure(row=i)
