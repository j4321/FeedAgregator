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


Desktop category widget
"""
from babel.dates import format_datetime
from datetime import datetime
from locale import getlocale
from tkinter.font import Font
from tkinter import Toplevel, BooleanVar, Menu, StringVar, Canvas, TclError
from tkinter.ttk import Style, Label, Separator, Sizegrip, Frame, Button
from feedagregatorlib.constants import CONFIG, FEEDS, APP_NAME, add_trace, \
    LATESTS, feed_get_latest, save_latests
from feedagregatorlib.messagebox import askokcancel
from feedagregatorlib.tkinterhtml import HtmlFrame
from feedagregatorlib.toggledframe import ToggledFrame
from feedagregatorlib.autoscrollbar import AutoScrollbar
from ewmh import EWMH, ewmh
from webbrowser import open as webopen
import configparser
import pickle


class CatWidget(Toplevel):
    def __init__(self, master, category):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.attributes('-type', 'splash')
        self.minsize(50, 50)

        self.category = category

        # control main menu checkbutton
        self.variable = BooleanVar(self, False)

        self._position = StringVar(self, LATESTS.get(self.category, 'position'))
        add_trace(self._position, 'write', self._position_trace)

        self.ewmh = EWMH()
        self.title('feedagregator.widget.{}'.format(self.category.replace(' ', '_')))
        self.withdraw()

        self.feeds = {}
        self.x = None
        self.y = None

        self._sort_order = StringVar(self, LATESTS.get(category, 'sort_order', fallback='A-Z'))
        add_trace(self._sort_order, 'write', self._order_trace)

        # --- menu
        self.menu = Menu(self, tearoff=False)
        menu_sort = Menu(self.menu, tearoff=False)
        menu_sort.add_radiobutton(label='A-Z',
                                  variable=self._sort_order, value='A-Z',
                                  command=lambda: self._sort_by_name(reverse=False))
        menu_sort.add_radiobutton(label='Z-A',
                                  variable=self._sort_order, value='Z-A',
                                  command=lambda: self._sort_by_name(reverse=True))
        menu_sort.add_radiobutton(label=_('Oldest first'),
                                  variable=self._sort_order, value='oldest',
                                  command=lambda: self._sort_by_date(reverse=False))
        menu_sort.add_radiobutton(label=_('Most recent first'),
                                  variable=self._sort_order, value='latest',
                                  command=lambda: self._sort_by_date(reverse=True))
        menu_pos = Menu(self.menu, tearoff=False)
        menu_pos.add_radiobutton(label=_('Normal'), value='normal',
                                 variable=self._position, command=self._change_position)
        menu_pos.add_radiobutton(label=_('Above'), value='above',
                                 variable=self._position, command=self._change_position)
        menu_pos.add_radiobutton(label=_('Below'), value='below',
                                 variable=self._position, command=self._change_position)
        self.menu.add_cascade(label=_('Sort'), menu=menu_sort)
        self.menu.add_cascade(label=_('Position'), menu=menu_pos)
        self.menu.add_command(label=_('Hide'), command=self.withdraw)
        self.menu.add_command(label=_('Open all'), command=self.open_all)
        self.menu.add_command(label=_('Close all'), command=self.close_all)
        if category != 'All':
            self.menu.add_command(label=_('Remove category'), command=self.remove_cat)

        # --- elements
        title = _('Feeds: Latests') if category == 'All' else _('Feeds: {category}').format(category=category)
        frame = Frame(self, style='widget.TFrame')
        Button(frame, style='widget.close.TButton',
               command=self.withdraw).pack(side='left')
        label = Label(frame, text=title, style='widget.title.TLabel',
                      anchor='center')
        label.pack(side='left', fill='x', expand=True)
        frame.grid(row=0, columnspan=2, padx=4, pady=4, sticky='ew')

        sep = Separator(self, style='widget.Horizontal.TSeparator')
        sep.grid(row=1, columnspan=2, sticky='ew')
        self.canvas = Canvas(self, highlightthickness=0)
        self.canvas.grid(row=2, column=0, sticky='ewsn', padx=(2, 8), pady=(2, 4))
        scroll = AutoScrollbar(self, orient='vertical',
                               style='widget.Vertical.TScrollbar',
                               command=self.canvas.yview)
        scroll.grid(row=2, column=1, sticky='ns', pady=(2, 14))
        self.canvas.configure(yscrollcommand=scroll.set)
        self.display = Frame(self.canvas, style='widget.TFrame')
        self.canvas.create_window(0, 0, anchor='nw', window=self.display, tags=('display',))

        self.display.columnconfigure(0, weight=1)

        # --- style
        self.style = Style(self)
        self._font_size = 10
        self.update_style()

        self.init_feed_display()

        corner = Sizegrip(self, style="widget.TSizegrip")
        corner.place(relx=1, rely=1, anchor='se')

        geometry = LATESTS.get(self.category, 'geometry')
        if geometry:
            self.geometry(geometry)
        self.update_idletasks()
        if LATESTS.getboolean(self.category, 'visible'):
            self.deiconify()

        # --- bindings
        self.bind('<3>', lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        for widget in [label, self.canvas, sep]:
            widget.bind('<ButtonPress-1>', self._start_move)
            widget.bind('<ButtonRelease-1>', self._stop_move)
            widget.bind('<B1-Motion>', self._move)
        self.bind('<Configure>', self._on_configure)
        self.bind('<Map>', self._change_position)
        self.bind('<4>', lambda e: self._scroll(-1))
        self.bind('<5>', lambda e: self._scroll(1))

        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def remove_cat(self):
        rep = True
        if CONFIG.getboolean('General', 'confirm_cat_remove', fallback=True):
            rep = askokcancel(_('Confirmation'),
                              _('Do you want to remove the category {category}?').format(category=self.category))
        if rep:
            for title in self.feeds:
                FEEDS.set(title, 'category', '')
            self.master.category_remove(self.category)

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
            if self.category in ['All', FEEDS.get(title, 'category', fallback='')]:
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
        self.attributes('-alpha', CONFIG.getint('Widget', 'alpha') / 100)
        text_font = Font(self, font=CONFIG.get('Widget', 'font')).actual()
        bg = CONFIG.get('Widget', 'background')
        feed_bg = CONFIG.get('Widget', 'feed_background', fallback='gray20')
        feed_fg = CONFIG.get('Widget', 'feed_foreground', fallback='white')

        self._stylesheet = """
body {
  background-color: %(bg)s;
  color: %(fg)s;
  font-family: %(family)s;
  font-weight: %(weight)s;
  font-style: %(slant)s;
}

ul {
padding-left: 5px;
}

ol {
padding-left: 5px;
}

#title {
  font-weight: bold;
  font-size: large;
}

a {
  color: %(link)s;
  font-style: italic;
}

code {font-family: monospace;}

a:hover {
  font-style: italic;
  border-bottom: 1px solid %(link)s;
}
""" % (dict(bg=feed_bg, fg=feed_fg, link=CONFIG.get('Widget', 'link_color', fallback='#89B9F6'), **text_font))

        self.configure(bg=bg)
        self.canvas.configure(background=bg)
        self._font_size = text_font['size']
        for tf, l in self.feeds.values():
            l.set_style(self._stylesheet)
            l.set_font_size(self._font_size)

    def withdraw(self):
        Toplevel.withdraw(self)
        self.variable.set(False)

    def deiconify(self):
        Toplevel.deiconify(self)
        self.variable.set(True)

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

    def _position_trace(self, *args):
        LATESTS.set(self.category, 'position', self._position.get())
        save_latests()

    def _order_trace(self, *args):
        LATESTS.set(self.category, 'sort_order', self._sort_order.get())
        save_latests()

    def _sort_by_date(self, reverse):
        titles = sorted(self.feeds, reverse=reverse, key=lambda x: FEEDS.get(x, 'updated'))
        for i, title in enumerate(titles):
            self.feeds[title][0].grid_configure(row=i)

    def _scroll(self, delta):
        top, bottom = self.canvas.yview()
        top += delta * 0.05
        top = min(max(top, 0), 1)
        self.canvas.yview_moveto(top)

    def _change_position(self, event=None):
        '''Make widget sticky and set its position with respects to the other windows.'''
        pos = self._position.get()
        try:
            for w in self.ewmh.getClientList():
                if w.get_wm_name() == self.title():
                    self.ewmh.setWmState(w, 1, '_NET_WM_STATE_STICKY')
                    if pos == 'above':
                        self.ewmh.setWmState(w, 1, '_NET_WM_STATE_ABOVE')
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_BELOW')
                    elif pos == 'below':
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_ABOVE')
                        self.ewmh.setWmState(w, 1, '_NET_WM_STATE_BELOW')
                    else:
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_BELOW')
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_ABOVE')
            self.ewmh.display.flush()
        except ewmh.display.error.BadWindow:
            pass

    def _on_configure(self, event):
        if event.widget is self:
            geometry = self.geometry()
            if geometry != '1x1+0+0':
                LATESTS.set(self.category, 'geometry', geometry)
                save_latests()
        elif event.widget in [self.canvas, self.display]:
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
            self.canvas.itemconfigure('display', width=self.canvas.winfo_width() - 4)

    def _start_move(self, event):
        self.x = event.x
        self.y = event.y
        self.configure(cursor='fleur')
        self.display.configure(cursor='fleur')

    def _stop_move(self, event):
        self.x = None
        self.y = None
        self.configure(cursor='arrow')
        self.display.configure(cursor='arrow')

    def _move(self, event):
        if self.x is not None and self.y is not None:
            deltax = event.x - self.x
            deltay = event.y - self.y
            x = self.winfo_x() + deltax
            y = self.winfo_y() + deltay
            self.geometry("+%s+%s" % (x, y))
