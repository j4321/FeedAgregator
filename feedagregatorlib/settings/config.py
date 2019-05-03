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


Config dialog
"""
from tkinter import Toplevel, Menu, StringVar
from tkinter.ttk import Separator, Menubutton, Button, Label, Frame, \
    Notebook, Entry, Style, Checkbutton

from PIL.ImageTk import PhotoImage

from feedagregatorlib.constants import CONFIG, TOOLKITS, IM_COLOR, APP_NAME,\
    LANGUAGES, REV_LANGUAGES
from feedagregatorlib.messagebox import showinfo
from .color import ColorFrame
from .opacity import OpacityFrame
from .font import FontFrame


class Config(Toplevel):
    def __init__(self, master):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.title(_("Settings"))
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.resizable(True, True)
        self.minsize(470, 574)

        style = Style(self)
        self._bg = style.lookup('TFrame', 'background')

        self.notebook = Notebook(self)
        self._validate = self.register(self._validate_entry_nb)

        self.img_color = PhotoImage(master=self, file=IM_COLOR)

        self.lang = StringVar(self, LANGUAGES[CONFIG.get("General", "language")])
        self.gui = StringVar(self, CONFIG.get("General", "trayicon").capitalize())

        self._init_general()
        self._init_widget()

        self.notebook.grid(sticky='ewsn', row=0, column=0, columnspan=2)
        Button(self, text=_('Ok'), command=self.ok).grid(row=1, column=0,
                                                         sticky='e', padx=4,
                                                         pady=10)
        Button(self, text=_('Cancel'), command=self.destroy).grid(row=1,
                                                                  column=1,
                                                                  sticky='w',
                                                                  padx=4,
                                                                  pady=10)

    def _init_general(self):
        frame_general = Frame(self)
        self.notebook.add(frame_general, text=_("General"))
        # --- Language
        Label(frame_general, text=_("Language")).grid(row=0, column=0,
                                                      padx=8, pady=4, sticky="e")

        menu_lang = Menu(frame_general, tearoff=False, background=self._bg)
        mb = Menubutton(frame_general, menu=menu_lang, textvariable=self.lang)
        mb.grid(row=0, column=1, padx=8, pady=4, sticky="w")
        for lang in LANGUAGES:
            language = LANGUAGES[lang]
            menu_lang.add_radiobutton(label=language, value=language,
                                      variable=self.lang, command=self.translate)

        # --- gui toolkit
        Label(frame_general,
              text=_("GUI Toolkit for the system tray icon")).grid(row=2, column=0,
                                                                   padx=8, pady=4,
                                                                   sticky="e")

        menu_gui = Menu(frame_general, tearoff=False, background=self._bg)
        Menubutton(frame_general, menu=menu_gui, width=9,
                   textvariable=self.gui).grid(row=2, column=1,
                                               padx=8, pady=4, sticky="w")
        for toolkit, b in TOOLKITS.items():
            if b:
                menu_gui.add_radiobutton(label=toolkit.capitalize(),
                                         value=toolkit.capitalize(),
                                         variable=self.gui,
                                         command=self.change_gui)
        # --- Update delay
        Label(frame_general,
              text=_("Feed update delay (min)")).grid(row=4, column=0,
                                                      padx=8, pady=4,
                                                      sticky="e")
        self.entry_delay = Entry(frame_general, width=10, justify='center',
                                 validate='key',
                                 validatecommand=(self._validate, '%P'))
        self.entry_delay.grid(row=4, column=1, padx=8, pady=4, sticky='w')
        self.entry_delay.insert(0, CONFIG.getint('General', 'update_delay') // 60000)
        # --- image loading timeout
        Label(frame_general,
              text=_("Image loading timeout (s)")).grid(row=5, column=0,
                                                        padx=8, pady=4,
                                                        sticky="e")
        self.entry_timeout = Entry(frame_general, width=10, justify='center',
                                   validate='key',
                                   validatecommand=(self._validate, '%P'))
        self.entry_timeout.grid(row=5, column=1, padx=8, pady=4, sticky='w')
        self.entry_timeout.insert(0, CONFIG.getint('General', 'img_timeout', fallback=10))
        # --- Notifications
        self.notifications = Checkbutton(frame_general,
                                         text=_("Activate notifications"))
        self.notifications.grid(row=6, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'notifications', fallback=True):
            self.notifications.state(('selected', '!alternate'))
        else:
            self.notifications.state(('!selected', '!alternate'))

        # --- Confirm remove feed
        self.confirm_feed_rem = Checkbutton(frame_general,
                                            text=_("Show confirmation dialog before removing feed"))
        self.confirm_feed_rem.grid(row=7, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'confirm_feed_remove', fallback=True):
            self.confirm_feed_rem.state(('selected', '!alternate'))
        else:
            self.confirm_feed_rem.state(('!selected', '!alternate'))
        # --- Confirm remove cat
        self.confirm_cat_rem = Checkbutton(frame_general,
                                           text=_("Show confirmation dialog before removing category"))
        self.confirm_cat_rem.grid(row=8, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'confirm_cat_remove', fallback=True):
            self.confirm_cat_rem.state(('selected', '!alternate'))
        else:
            self.confirm_cat_rem.state(('!selected', '!alternate'))
        # --- Confirm update
        self.confirm_update = Checkbutton(frame_general,
                                          text=_("Check for updates on start-up"))
        self.confirm_update.grid(row=9, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'check_update', fallback=True):
            self.confirm_update.state(('selected', '!alternate'))
        else:
            self.confirm_update.state(('!selected', '!alternate'))

        # --- Splash supported
        self.splash_support = Checkbutton(frame_general,
                                          text=_("Check this box if the widgets disappear when you click"))
        self.splash_support.grid(row=10, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if not CONFIG.getboolean('General', 'splash_supported', fallback=True):
            self.splash_support.state(('selected', '!alternate'))
        else:
            self.splash_support.state(('!selected', '!alternate'))

    def _init_widget(self):
        frame_widget = Frame(self)
        self.notebook.add(frame_widget, text=_('Widget'))

        # --- font
        frame_font = Frame(frame_widget)
        self.title_font = FontFrame(frame_font, CONFIG.get("Widget", "font_title"), True)
        self.text_font = FontFrame(frame_font, CONFIG.get("Widget", "font"))
        frame_font.columnconfigure(1, weight=1)
        Label(frame_font,
              text=_('Title')).grid(row=0, column=0, sticky='nw', padx=4, pady=4)
        self.title_font.grid(row=0, column=1)
        Separator(frame_font, orient='horizontal').grid(row=1, columnspan=2,
                                                        sticky='ew', padx=4,
                                                        pady=4)
        Label(frame_font,
              text=_('Text')).grid(row=2, column=0, sticky='nw', padx=4, pady=4)
        self.text_font.grid(row=2, column=1)

        # --- opacity
        self.opacity_frame = OpacityFrame(frame_widget, CONFIG.get("Widget", "alpha"))

        # --- colors
        frame_color = Frame(frame_widget)
        frame_color.columnconfigure(1, weight=1)
        frame_color.columnconfigure(3, weight=1)
        self.color_bg = ColorFrame(frame_color,
                                   CONFIG.get("Widget", "background"),
                                   _('Background color'))
        self.color_fg = ColorFrame(frame_color,
                                   CONFIG.get("Widget", "foreground"),
                                   _('Foreground color'))
        self.color_feed_bg = ColorFrame(frame_color,
                                        CONFIG.get("Widget", "feed_background"),
                                        _('Background color'))
        self.color_feed_fg = ColorFrame(frame_color,
                                        CONFIG.get("Widget", "feed_foreground"),
                                        _('Foreground color'))
        self.color_link = ColorFrame(frame_color,
                                     CONFIG.get("Widget", "link_color"),
                                     _('Link color'))
        Label(frame_color,
              text=_('General')).grid(row=0, column=0, sticky='w', padx=4, pady=2)
        self.color_bg.grid(row=0, column=1, sticky='e', padx=4, pady=2)
        self.color_fg.grid(row=1, column=1, sticky='e', padx=4, pady=2)

        Separator(frame_color, orient='horizontal').grid(row=2, columnspan=4,
                                                         sticky='ew', padx=4,
                                                         pady=4)
        Label(frame_color,
              text=_('Feed entry')).grid(row=3, column=0, sticky='w', padx=4,
                                         pady=2)
        self.color_feed_bg.grid(row=3, column=1, sticky='e', padx=4, pady=2)
        self.color_feed_fg.grid(row=4, column=1, sticky='e', padx=4, pady=2)
        self.color_link.grid(row=5, column=1, sticky='e', padx=4, pady=2)

        # --- pack
        Label(frame_widget, text=_('Font'),
              font='TkDefaultFont 9 bold', anchor='w').pack(padx=4, fill='x')
        frame_font.pack(fill='x', padx=14)
        Separator(frame_widget, orient='horizontal').pack(fill='x', pady=6)
        self.opacity_frame.pack(padx=(4, 10), fill='x')
        Separator(frame_widget, orient='horizontal').pack(fill='x', pady=6)
        Label(frame_widget, text=_('Colors'),
              font='TkDefaultFont 9 bold', anchor='w').pack(padx=4, fill='x')
        frame_color.pack(fill='x', padx=14)

    def display_label(self, value):
        self.opacity_label.configure(text=" {val} %".format(val=int(float(value))))

    def translate(self):
        showinfo("Information",
                 _("The language setting will take effect after restarting the application"),
                 parent=self)

    @staticmethod
    def _config_size(variable, font):
        size = variable.get()
        if size:
            font.configure(size=size)

    @staticmethod
    def _validate_entry_nb(P):
        """ Allow only to enter numbers"""
        parts = P.split(".")
        b = len(parts) < 3 and P != "."
        for p in parts:
            b = b and (p == "" or p.isdigit())
        return b

    def change_gui(self):
        showinfo("Information",
                 _("The GUI Toolkit setting will take effect after restarting the application"),
                 parent=self)

    def ok(self):
        # --- general
        CONFIG.set("General", "language", REV_LANGUAGES[self.lang.get()])
        CONFIG.set("General", "trayicon", self.gui.get().lower())
        CONFIG.set("General", "update_delay", "%i" % (int(self.entry_delay.get()) * 60000))
        CONFIG.set("General", "img_timeout", "%i" % (int(self.entry_timeout.get())))
        CONFIG.set('General', 'confirm_feed_remove', str(self.confirm_feed_rem.instate(('selected',))))
        CONFIG.set('General', 'confirm_cat_remove', str(self.confirm_cat_rem.instate(('selected',))))
        CONFIG.set('General', 'check_update', str(self.confirm_update.instate(('selected',))))
        CONFIG.set('General', 'splash_supported', str(not self.splash_support.instate(('selected',))))
        CONFIG.set('General', 'notifications', str(self.notifications.instate(('selected',))))
        # --- widget
        CONFIG.set("Widget", "alpha", "%i" % self.opacity_frame.get_opacity())

        font_title_dic = self.title_font.get_font()
        font_title_dic['underline'] = 'underline' if font_title_dic['underline'] else ''
        font_title_dic['family'] = font_title_dic['family'].replace(' ', '\ ')
        CONFIG.set("Widget", "font_title", "{family} {size} {weight} {slant} {underline}".format(**font_title_dic))
        font_text_dic = self.text_font.get_font()
        font_text_dic['family'] = font_text_dic['family'].replace(' ', '\ ')
        CONFIG.set("Widget", "font", "{family} {size}".format(**font_text_dic))
        CONFIG.set("Widget", "foreground", self.color_fg.get_color())
        CONFIG.set("Widget", "background", self.color_bg.get_color())
        CONFIG.set("Widget", "feed_foreground", self.color_feed_fg.get_color())
        CONFIG.set("Widget", "feed_background", self.color_feed_bg.get_color())
        CONFIG.set("Widget", "link_color", self.color_link.get_color())
        self.destroy()
