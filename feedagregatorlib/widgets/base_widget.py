#! /usr/bin/python3
# -*- coding:Utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2019 Juliette Monsel <j_4321@protonmail.com>

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


Base desktop widget
"""
from datetime import datetime
from locale import getlocale
from webbrowser import open as webopen
from tkinter import Toplevel, BooleanVar, Menu, StringVar, Canvas, TclError
from tkinter.ttk import Style, Label, Separator, Sizegrip, Frame, Button
from tkinter.font import Font

from ewmh import EWMH, ewmh
from babel.dates import format_datetime

from feedagregatorlib.constants import CONFIG, APP_NAME, add_trace
from feedagregatorlib.autoscrollbar import AutoScrollbar
from feedagregatorlib.toggledframe import ToggledFrame
from feedagregatorlib.tkinterhtml import HtmlFrame


class BaseWidget(Toplevel):
    def __init__(self, master, name, config, save_config):
        """Create base desktop widget."""
        Toplevel.__init__(self, master, class_=APP_NAME)

        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)
        self.minsize(50, 50)
        self.protocol('WM_DELETE_WINDOW', self.withdraw)

        self.ewmh = EWMH()

        self.name = name
        self.config = config            # configparser
        self.save_config = save_config  # save config method

        # get splash window type compatibility
        if CONFIG.getboolean('General', 'splash_supported', fallback=True):
            self.attributes('-type', 'splash')
        else:
            self.attributes('-type', 'toolbar')

        # control main menu checkbutton
        self.variable = BooleanVar(self, False)
        # save widget's position
        self._position = StringVar(self, self.config.get(name, 'position', fallback='normal'))
        add_trace(self._position, 'write', self._position_trace)

        self.title('feedagregator.widget.{}'.format(name.replace(' ', '_')))
        self.withdraw()

        # window dragging
        self.x = None
        self.y = None

        # --- menu
        self._create_menu()

        # --- elements
        # --- --- title bar
        frame = Frame(self, style='widget.TFrame')
        Button(frame, style='widget.close.TButton',
               command=self.withdraw).pack(side='left')
        self.label = Label(frame, text=name, style='widget.title.TLabel',
                           anchor='center')
        self.label.pack(side='left', fill='x', expand=True)
        frame.grid(row=0, columnspan=2, padx=4, pady=4, sticky='ew')

        sep = Separator(self, style='widget.Horizontal.TSeparator')
        sep.grid(row=1, columnspan=2, sticky='ew')
        # --- --- widget body
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

        # --- resizing and geometry
        corner = Sizegrip(self, style="widget.TSizegrip")
        corner.place(relx=1, rely=1, anchor='se', bordermode='outside')

        geometry = self.config.get(self.name, 'geometry')
        if geometry:
            self.geometry(geometry)
        self.update_idletasks()
        if self.config.getboolean(self.name, 'visible', fallback=True):
            self.deiconify()

        # --- bindings
        self.bind('<3>', lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        for widget in [self.label, self.canvas, sep]:
            widget.bind('<ButtonPress-1>', self._start_move)
            widget.bind('<ButtonRelease-1>', self._stop_move)
            widget.bind('<B1-Motion>', self._move)
        self.label.bind('<Map>', self._change_position)
        self.bind('<Configure>', self._on_configure)
        self.bind('<4>', lambda e: self._scroll(-1))
        self.bind('<5>', lambda e: self._scroll(1))

        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

        self.populate_widget()

        if not CONFIG.getboolean('General', 'splash_supported', fallback=True) and self.config.getboolean(self.name, 'visible', fallback=True):
            Toplevel.withdraw(self)
            Toplevel.deiconify(self)

    def _create_menu(self):
        self.menu = Menu(self, tearoff=False)
        self.menu_sort = Menu(self.menu, tearoff=False)

        menu_pos = Menu(self.menu, tearoff=False)
        menu_pos.add_radiobutton(label=_('Normal'), value='normal',
                                 variable=self._position, command=self._change_position)
        menu_pos.add_radiobutton(label=_('Above'), value='above',
                                 variable=self._position, command=self._change_position)
        menu_pos.add_radiobutton(label=_('Below'), value='below',
                                 variable=self._position, command=self._change_position)
        self.menu.add_cascade(label=_('Sort'), menu=self.menu_sort)
        self.menu.add_cascade(label=_('Position'), menu=menu_pos)
        self.menu.add_command(label=_('Hide'), command=self.withdraw)
        self.menu.add_command(label=_('Open all'), command=self.open_all)
        self.menu.add_command(label=_('Close all'), command=self.close_all)

    def populate_widget(self):
        pass  # to be overriden by subclass

    def open_all(self):
        pass  # to be overriden by subclass

    def close_all(self):
        pass  # to be overriden by subclass

    def entry_add(self, title, date, summary, url):
        """Display entry and return the toggleframe and htmlframe."""

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
        l.set_content(summary)
        l.set_style(self._stylesheet)
        l.set_font_size(self._font_size)
        tf.interior.configure(style='widget.interior.TFrame')
        tf.interior.rowconfigure(0, weight=1)
        tf.interior.columnconfigure(0, weight=1)
        l.grid(padx=4, sticky='eswn')
        b = Button(tf.interior, text='Open', style='widget.TButton',
                   command=lambda: webopen(url))
        b.grid(pady=4, padx=6, sticky='e')
        tf.grid(sticky='we', row=len(self.entries), pady=2, padx=(8, 4))
        tf.bind("<<ToggledFrameOpen>>", unwrap)
        l.bind("<Configure>", resize)
        return tf, l, b

    def update_position(self):
        if self._position.get() == 'normal':
            if CONFIG.getboolean('General', 'splash_supported', fallback=True):
                self.attributes('-type', 'splash')
            else:
                self.attributes('-type', 'toolbar')
        if self.variable.get():
            Toplevel.withdraw(self)
            Toplevel.deiconify(self)

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

    def withdraw(self):
        Toplevel.withdraw(self)
        self.variable.set(False)

    def deiconify(self):
        Toplevel.deiconify(self)
        self.variable.set(True)

    def _scroll(self, delta):
        top, bottom = self.canvas.yview()
        top += delta * 0.05
        top = min(max(top, 0), 1)
        self.canvas.yview_moveto(top)

    def _position_trace(self, *args):
        self.config.set(self.name, 'position', self._position.get())
        self.save_config()

    def _change_position(self, event=None):
        '''Make widget sticky and set its position with respects to the other windows.'''
        pos = self._position.get()
        splash_supp = CONFIG.getboolean('General', 'splash_supported', fallback=True)
        try:
            for w in self.ewmh.getClientList():
                if w.get_wm_name() == self.title():
                    self.ewmh.setWmState(w, 1, '_NET_WM_STATE_STICKY')
                    self.ewmh.setWmState(w, 1, '_NET_WM_STATE_SKIP_TASKBAR')
                    self.ewmh.setWmState(w, 1, '_NET_WM_STATE_SKIP_PAGER')
                    if pos == 'above':
                        self.attributes('-type', 'dock')
                        self.ewmh.setWmState(w, 1, '_NET_WM_STATE_ABOVE')
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_BELOW')
                    elif pos == 'below':
                        self.attributes('-type', 'desktop')
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_ABOVE')
                        self.ewmh.setWmState(w, 1, '_NET_WM_STATE_BELOW')
                    else:
                        if splash_supp:
                            self.attributes('-type', 'splash')
                        else:
                            self.attributes('-type', 'toolbar')
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_BELOW')
                        self.ewmh.setWmState(w, 0, '_NET_WM_STATE_ABOVE')
            self.ewmh.display.flush()
            if event is None and not splash_supp:
                Toplevel.withdraw(self)
                Toplevel.deiconify(self)
        except ewmh.display.error.BadWindow:
            pass

    def _on_configure(self, event):
        if event.widget is self:
            geometry = self.geometry()
            if geometry != '1x1+0+0':
                self.config.set(self.name, 'geometry', geometry)
                self.save_config()
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
