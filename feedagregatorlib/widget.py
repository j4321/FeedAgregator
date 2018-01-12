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


Desktop widget
"""
from babel.dates import format_datetime
from datetime import datetime
from locale import getlocale
from tkinter.font import Font
from tkinter import Toplevel, BooleanVar, Menu, StringVar, Canvas, TclError
from tkinter.ttk import Style, Label, Separator, Sizegrip, Frame, Button
from feedagregatorlib.constants import CONFIG, FEEDS, active_color, APP_NAME, add_trace
from feedagregatorlib.tkinterhtml import HtmlFrame
from feedagregatorlib.toggledframe import ToggledFrame
from ewmh import EWMH
from webbrowser import open as webopen


class Widget(Toplevel):
    def __init__(self, master):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.attributes('-type', 'splash')
        self.minsize(50, 50)

        # control main menu checkbutton
        self.variable = BooleanVar(self, False)

        self._position = StringVar(self, CONFIG.get('Widget', 'position'))
        add_trace(self._position, 'write',
                  lambda *x: CONFIG.set('Widget', 'position', self._position.get()))

        self.ewmh = EWMH()
        self.title('feedagregator.widget')
        self.withdraw()

        self.feeds = {}
        self.x = None
        self.y = None

        # --- menu
        self.menu = Menu(self, tearoff=False)
        menu_sort = Menu(self.menu, tearoff=False)
        menu_sort.add_command(label='A-Z', command=lambda: self._sort(reverse=False))
        menu_sort.add_command(label='Z-A', command=lambda: self._sort(reverse=True))
        menu_sort.add_command(label=_('Oldest first'), command=lambda: self._sort_by_date(reverse=False))
        menu_sort.add_command(label=_('Most recent first'), command=lambda: self._sort_by_date(reverse=True))
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

        # --- elements
        label = Label(self, text=_('Feeds: Latests'), style='widget.title.TLabel',
                      anchor='center')
        label.pack(pady=4, fill='x')
        sep = Separator(self, style='widget.TSeparator')
        sep.pack(fill='x')
        self.canvas = Canvas(self, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=2, pady=2)
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

        geometry = CONFIG.get('Widget', 'geometry')
        if geometry:
            self.geometry(geometry)
        self.update_idletasks()
        if CONFIG.getboolean('Widget', 'visible'):
            self.deiconify()

        # --- bindings
        self.bind('<3>', lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        for widget in [label, self.canvas, sep]:
            widget.bind('<ButtonPress-1>', self._start_move)
            widget.bind('<ButtonRelease-1>', self._stop_move)
            widget.bind('<B1-Motion>', self._move)
        self.bind('<Configure>', self._on_configure)
        self.bind('<4>', lambda e: self._scroll(-1))
        self.bind('<5>', lambda e: self._scroll(1))

        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def init_feed_display(self):
        for tf, l in self.feeds.values():
            tf.destroy()
        self.feeds.clear()
        for title in sorted(FEEDS.sections(), key=lambda x: x.lower()):
            url = FEEDS.get(title, 'url')
            latest = FEEDS.get(title, 'latest')
            date = FEEDS.get(title, 'updated')
            self.add_feed(title, latest, url, date)
            if not FEEDS.getboolean(title, 'in_latests'):
                self.hide_feed(title)

    def add_feed(self, title, latest, url, date):
        """Display feed."""

        def unwrap(event):
            try:
                h = l.html.bbox()[-1]
            except TclError:
                pass
            else:
                l.configure(height=h)

        formatted_date = format_datetime(datetime.strptime(date, '%Y-%m-%d %H:%M'),
                                         'short', locale=getlocale()[0])

        tf = ToggledFrame(self.display, text="{} - {}".format(title, formatted_date),
                          style='widget.TFrame')
        l = HtmlFrame(tf.interior, height=50, style='widget.TFrame')
        l.set_content(latest)
        l.set_style(self._stylesheet)
        l.set_font_size(self._font_size)
        tf.interior.rowconfigure(0, weight=1)
        tf.interior.columnconfigure(1, weight=1)
        Frame(tf.interior, height=50, width=1,
              style='widget.line.TFrame').grid(row=0, column=0, rowspan=2, sticky='ns')
        l.grid(row=0, column=1, padx=4, sticky='eswn')
        Button(tf.interior, text='Open', style='widget.TButton',
               command=lambda: webopen(url)).grid(row=1, column=1, pady=4, padx=6, sticky='e')
        tf.grid(sticky='we', row=len(self.feeds), pady=2, padx=(8, 4))
        tf.bind("<<ToggledFrameUnwrap>>", unwrap)
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
        self.feeds[new_name][0].label.configure(text=new_name)

    def update_display(self, title, latest, date):
        formatted_date = format_datetime(datetime.strptime(date, '%Y-%m-%d %H:%M'),
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
        fg = CONFIG.get('Widget', 'foreground')

        self._stylesheet = """
body {
  background-color: %(bg)s;
  color: %(fg)s;
  font-family: %(family)s;
  font-weight: %(weight)s;
  font-style: %(slant)s;
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
""" % (dict(bg=bg, fg=fg, link=CONFIG.get('Widget', 'link_color'), **text_font))

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

    def _sort(self, reverse):
        titles = sorted(self.feeds, reverse=reverse, key=lambda x: x.lower())
        for i, title in enumerate(titles):
            self.feeds[title][0].grid_configure(row=i)

    def _sort_by_date(self, reverse):
        titles = sorted(self.feeds, reverse=reverse, key=lambda x: FEEDS.get(x, 'updated'))
        for i, title in enumerate(titles):
            self.feeds[title][0].grid_configure(row=i)

    def _scroll(self, delta):
        top, bottom = self.canvas.yview()
        top += delta * 0.05
        top = min(max(top, 0), 1)
        self.canvas.yview_moveto(top)

    def _change_position(self):
        ''' make widget sticky '''
        for w in self.ewmh.getClientList():
            if w.get_wm_name() == 'feedagregator.widget':
                self.ewmh.setWmState(w, 1, '_NET_WM_STATE_STICKY')
        pos = self._position.get()
        if pos == 'above':
            for w in self.ewmh.getClientList():
                if w.get_wm_name() == 'feedagregator.widget':
                    self.ewmh.setWmState(w, 1, '_NET_WM_STATE_ABOVE')
                    self.ewmh.setWmState(w, 0, '_NET_WM_STATE_BELOW')
        elif pos == 'below':
            for w in self.ewmh.getClientList():
                if w.get_wm_name() == 'feedagregator.widget':
                    self.ewmh.setWmState(w, 0, '_NET_WM_STATE_ABOVE')
                    self.ewmh.setWmState(w, 1, '_NET_WM_STATE_BELOW')
        else:
            for w in self.ewmh.getClientList():
                if w.get_wm_name() == 'feedagregator.widget':
                    self.ewmh.setWmState(w, 0, '_NET_WM_STATE_BELOW')
                    self.ewmh.setWmState(w, 0, '_NET_WM_STATE_ABOVE')
        self.ewmh.display.flush()

    def _on_configure(self, event):
        if event.widget is self:
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
            self.canvas.itemconfigure('display', width=self.canvas.winfo_width() - 4)
            geometry = self.geometry()
            if geometry != '1x1+0+0':
                CONFIG.set('Widget', 'geometry', geometry)
                self.update_idletasks()
                for tf, l in self.feeds.values():
                    if tf.winfo_ismapped():
                        try:
                            h = l.html.bbox()[-1]
                        except TclError:
                            self.after(10, lambda: self._on_configure(None))
                        else:
                            l.configure(height=h)

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
