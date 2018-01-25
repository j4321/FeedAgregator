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


Desktop widget for a single feed
"""
from babel.dates import format_datetime
from datetime import datetime
from locale import getlocale
from tkinter.font import Font
from tkinter import Toplevel, BooleanVar, Menu, StringVar, Canvas, TclError
from tkinter.ttk import Style, Label, Separator, Sizegrip, Frame, Button, Entry
from feedagregatorlib.constants import CONFIG, FEEDS, APP_NAME, add_trace
from feedagregatorlib.messagebox import askokcancel
from feedagregatorlib.tkinterhtml import HtmlFrame
from feedagregatorlib.toggledframe import ToggledFrame
from ewmh import EWMH
from webbrowser import open as webopen


class FeedWidget(Toplevel):
    def __init__(self, master, feed_name):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.feed_name = feed_name

        self.attributes('-type', 'splash')
        self.minsize(50, 50)

        # control main menu checkbutton
        self.variable = BooleanVar(self, False)

        self._position = StringVar(self, FEEDS.get(feed_name, 'position', fallback='normal'))
        add_trace(self._position, 'write',
                  lambda *x: FEEDS.set(feed_name, 'position', self._position.get()))

        self.ewmh = EWMH()
        self.title('feedagregator.widget.{}'.format(feed_name.replace(' ', '_')))
        self.withdraw()

        self.entries = []
        self.x = None
        self.y = None

        self._sort_is_reversed = BooleanVar(self,
                                            FEEDS.getboolean(self.feed_name,
                                                             'sort_is_reversed',
                                                             fallback=False))
        add_trace(self._sort_is_reversed, 'write',
                  lambda *args: FEEDS.set(self.feed_name, 'sort_is_reversed', str(self._sort_is_reversed.get())))

        # --- menu
        self.menu = Menu(self, tearoff=False)
        menu_sort = Menu(self.menu, tearoff=False)
        menu_sort.add_radiobutton(label=_('Oldest first'),
                                  variable=self._sort_is_reversed,
                                  value=True,
                                  command=self.sort_by_date)
        menu_sort.add_radiobutton(label=_('Most recent first'),
                                  variable=self._sort_is_reversed,
                                  value=False,
                                  command=self.sort_by_date)
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
        self.menu.add_command(label=_('Remove feed'), command=self.remove_feed)

        # --- elements
        self.label = Label(self, text=feed_name, style='widget.title.TLabel',
                           anchor='center')
        self.label.pack(padx=4, pady=4, fill='x')
        self.label.bind('<Double-1>', self.rename)
        sep = Separator(self, style='widget.TSeparator')
        sep.pack(fill='x')
        self.canvas = Canvas(self, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=(2, 8), pady=2)
        self.display = Frame(self.canvas, style='widget.TFrame')
        self.canvas.create_window(0, 0, anchor='nw', window=self.display, tags=('display',))

        self.display.columnconfigure(0, weight=1)

        # --- style
        self.style = Style(self)
        self._font_size = 10
        self.update_style()

        corner = Sizegrip(self, style="widget.TSizegrip")
        corner.place(relx=1, rely=1, anchor='se')

        geometry = FEEDS.get(self.feed_name, 'geometry')
        if geometry:
            self.geometry(geometry)
        self.update_idletasks()
        if FEEDS.getboolean(self.feed_name, 'visible', fallback=True):
            self.deiconify()

        # --- bindings
        self.bind('<3>', lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        for widget in [self.label, self.canvas, sep]:
            widget.bind('<ButtonPress-1>', self._start_move)
            widget.bind('<ButtonRelease-1>', self._stop_move)
            widget.bind('<B1-Motion>', self._move)
        self.bind('<Map>', self._change_position)
        self.bind('<Configure>', self._on_configure)
        self.bind('<4>', lambda e: self._scroll(-1))
        self.bind('<5>', lambda e: self._scroll(1))

        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def remove_feed(self):
        rep = True
        if CONFIG.getboolean('General', 'confirm_remove', fallback=True):
            rep = askokcancel(_('Confirmation'),
                              _('Do you want to remove the feed {feed}?').format(feed=self.feed_name))
        if rep:
            self.master.feed_remove(self.feed_name)

    def open_all(self):
        for tf, l in self.entries:
            tf.open()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def close_all(self):
        for tf, l in self.entries:
            tf.close()
        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def clear(self):
        for tf, l in self.entries:
            tf.destroy()
        self.entries.clear()

    def entry_add(self, title, date, summary, url, index=0):
        """Display entry."""

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

        formatted_date = format_datetime(datetime.strptime(date, '%Y-%m-%d %H:%M').astimezone(tz=None),
                                         'short', locale=getlocale()[0])

        tf = ToggledFrame(self.display, text="{} - {}".format(title, formatted_date),
                          style='widget.TFrame')
        l = HtmlFrame(tf.interior, height=50, style='widget.interior.TFrame')
        l.set_content(summary)
        l.set_style(self._stylesheet)
        l.set_font_size(self._font_size)
        tf.interior.configure(style='widget.interior.TFrame')
        tf.interior.rowconfigure(0, weight=1)
        tf.interior.columnconfigure(0, weight=1)
        l.grid(padx=4, sticky='eswn')
        Button(tf.interior, text='Open', style='widget.TButton',
               command=lambda: webopen(url)).grid(pady=4, padx=6, sticky='e')
        tf.grid(sticky='we', row=len(self.entries), pady=2, padx=(8, 4))
        tf.bind("<<ToggledFrameOpen>>", unwrap)
        l.bind("<Configure>", resize)
        if index == -1:
            self.entries.append((tf, l))
        else:
            self.entries.insert(index, (tf, l))

    def rename(self, event):

        def ok(event):
            name = entry.get()
            entry.destroy()
            if name:
                self.master.feed_rename(self.feed_name, name)

        entry = Entry(self, justify='center')
        entry.insert(0, self.feed_name)
        entry.selection_range(0, 'end')
        entry.place(in_=self.label, relwidth=1, relheight=1, x=0, y=0, anchor='nw')
        entry.bind('<Return>', ok)
        entry.bind('<Escape>', lambda e: entry.destroy())
        entry.bind('<FocusOut>', lambda e: entry.destroy())
        entry.focus_force()

    def rename_feed(self, new_name):
        self.feed_name = new_name
        self.title('feedagregator.widget.{}'.format(new_name.replace(' ', '_')))
        self.label.configure(text=new_name)

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
        for tf, l in self.entries:
            l.set_style(self._stylesheet)
            l.set_font_size(self._font_size)

    def withdraw(self):
        Toplevel.withdraw(self)
        self.variable.set(False)

    def deiconify(self):
        Toplevel.deiconify(self)
        self.variable.set(True)

    def sort_by_date(self):
        if self._sort_is_reversed.get():
            l = reversed(self.entries)
        else:
            l = self.entries
        for i, (tf, l) in enumerate(l):
            tf.grid_configure(row=i)

    def _scroll(self, delta):
        top, bottom = self.canvas.yview()
        top += delta * 0.05
        top = min(max(top, 0), 1)
        self.canvas.yview_moveto(top)

    def _change_position(self, event=None):
        '''Make widget sticky and set its position with respects to the other windows.'''
        pos = self._position.get()
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

    def _on_configure(self, event):
        if event.widget is self:
            geometry = self.geometry()
            if geometry != '1x1+0+0':
                FEEDS.set(self.feed_name, 'geometry', geometry)
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
