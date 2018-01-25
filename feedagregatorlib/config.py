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


Config dialog
"""
import tkinter.font as tkfont
from tkinter import Toplevel, Menu, StringVar, TclError
from tkinter.ttk import Separator, Menubutton, Button, Label, Frame, \
    Notebook, Entry, Scale, Style, Checkbutton, Combobox
from feedagregatorlib.constants import CONFIG, TOOLKITS, IM_COLOR, APP_NAME,\
    LANGUAGES, REV_LANGUAGES, add_trace, askcolor, PhotoImage
from feedagregatorlib.messagebox import showinfo
from feedagregatorlib.autocomplete import AutoCompleteCombobox


class Config(Toplevel):
    def __init__(self, master):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.title(_("Settings"))
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.resizable(False, True)

        style = Style(self)
        self._bg = style.lookup('TFrame', 'background')
        self.configure(bg=self._bg)

        self.notebook = Notebook(self)
        self._validate = self.register(self._validate_entry_nb)
        self._validate_title_size = self.register(lambda *args: self._validate_font_size(self.fonttitle_size, *args))
        self._validate_text_size = self.register(lambda *args: self._validate_font_size(self.font_size, *args))

        self.img_color = PhotoImage(master=self, file=IM_COLOR)

        self.lang = StringVar(self, LANGUAGES[CONFIG.get("General", "language")])
        self.gui = StringVar(self, CONFIG.get("General", "trayicon").capitalize())

        self._init_general()
        self._init_widget()

        self.notebook.grid(sticky='ewsn', row=0, column=0, columnspan=2)
        Button(self, text=_('Ok'), command=self.ok).grid(row=1, column=0,
                                                         sticky='e', padx=4,
                                                         pady=10)
        Button(self, text=_('Cancel'), command=self.destroy).grid(row=1, column=1,
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
        mb = Menubutton(frame_general, menu=menu_lang, width=9,
                        textvariable=self.lang)
        mb.grid(row=0, column=1, padx=8, pady=4, sticky="w")
        width = 0
        for lang in LANGUAGES:
            language = LANGUAGES[lang]
            width = max(width, len(language))
            menu_lang.add_radiobutton(label=language, value=language,
                                      variable=self.lang, command=self.translate)
        mb.configure(width=width)

        # Separator(self, orient='horizontal').grid(row=1, columnspan=2, sticky='ew')
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
        # Separator(self, orient='horizontal').grid(row=3, columnspan=2, sticky='ew')
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
        # --- Confirm remove feed
        self.confirm_feed_rem = Checkbutton(frame_general,
                                            text=_("Show confirmation dialog before removing feed"))
        self.confirm_feed_rem.grid(row=5, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'confirm_feed_remove', fallback=True):
            self.confirm_feed_rem.state(('selected', '!alternate'))
        else:
            self.confirm_feed_rem.state(('!selected', '!alternate'))
        # --- Confirm remove cat
        self.confirm_cat_rem = Checkbutton(frame_general,
                                           text=_("Show confirmation dialog before removing category"))
        self.confirm_cat_rem.grid(row=6, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'confirm_cat_remove', fallback=True):
            self.confirm_cat_rem.state(('selected', '!alternate'))
        else:
            self.confirm_cat_rem.state(('!selected', '!alternate'))
        # --- Confirm update
        self.confirm_update = Checkbutton(frame_general,
                                          text=_("Check for updates on start-up"))
        self.confirm_update.grid(row=7, column=0, padx=8, pady=4, columnspan=2, sticky='w')
        if CONFIG.getboolean('General', 'check_update', fallback=True):
            self.confirm_update.state(('selected', '!alternate'))
        else:
            self.confirm_update.state(('!selected', '!alternate'))

    def _init_widget(self):
        frame_widget = Frame(self)
        self.notebook.add(frame_widget, text=_('Widget'))

        # --- font
        frame_font = Frame(frame_widget)
        # ------- title
        fonttitle_frame = Frame(frame_font)
        self.title_font = tkfont.Font(self, font=CONFIG.get("Widget", "font_title"))
        sampletitle = Label(fonttitle_frame, text=_("Sample text"),
                            anchor="center", font=self.title_font,
                            style="prev.TLabel", relief="groove")

        sampletitle.grid(row=2, columnspan=2, padx=4, pady=6,
                         ipadx=4, ipady=4, sticky="eswn")
        self.fonts = list(set(tkfont.families()))
        self.fonts.append("TkDefaultFont")
        self.fonts.sort()

        self.title_font_family = StringVar(self, value=self.title_font.cget('family'))
        add_trace(self.title_font_family, 'write',
                  lambda *args: self.title_font.configure(family=self.title_font_family.get()))
        self.title_font_size = StringVar(self, value=self.title_font.cget('size'))
        add_trace(self.title_font_size, 'write',
                  lambda *args: self._config_size(self.title_font_size, self.title_font))
        self.title_font_bold = StringVar(self, value=self.title_font.cget('weight'))
        add_trace(self.title_font_bold, 'write',
                  lambda *args: self.title_font.configure(weight=self.title_font_bold.get()))
        self.title_font_italic = StringVar(self, value=self.title_font.cget('slant'))
        add_trace(self.title_font_italic, 'write',
                  lambda *args: self.title_font.configure(slant=self.title_font_italic.get()))

        w = max([len(f) for f in self.fonts])
        self.sizes = ["%i" % i for i in (list(range(6, 17)) + list(range(18, 32, 2)))]

        self.fonttitle_family = AutoCompleteCombobox(fonttitle_frame, values=self.fonts,
                                                     width=(w * 2) // 3,
                                                     textvariable=self.title_font_family,
                                                     exportselection=False)
        self.fonttitle_family.current(self.fonts.index(self.title_font.cget('family')))
        self.fonttitle_family.grid(row=0, column=0, padx=4, pady=4)
        self.fonttitle_size = Combobox(fonttitle_frame, values=self.sizes, width=5,
                                       exportselection=False,
                                       textvariable=self.title_font_size,
                                       validate="key",
                                       validatecommand=(self._validate_title_size, "%d", "%P", "%V"))
        self.fonttitle_size.current(self.sizes.index(str(self.title_font.cget('size'))))
        self.fonttitle_size.grid(row=0, column=1, padx=4, pady=4)

        frame_title_style = Frame(fonttitle_frame)
        frame_title_style.grid(row=1, columnspan=2, padx=4, pady=6)

        self.is_bold = Checkbutton(frame_title_style, text=_("Bold"),
                                   onvalue='bold', offvalue='normal',
                                   variable=self.title_font_bold)
        self.is_italic = Checkbutton(frame_title_style, text=_("Italic"),
                                     onvalue='italic', offvalue='roman',
                                     variable=self.title_font_italic)
        self.is_underlined = Checkbutton(frame_title_style, text=_("Underline"),
                                         command=lambda: self.title_font.configure(underline=self.is_underlined.instate(("selected",))))
        if self.title_font.cget('underline'):
            self.is_underlined.state(('selected', '!alternate'))
        else:
            self.is_underlined.state(('!selected', '!alternate'))
        self.is_bold.pack(side="left")
        self.is_italic.pack(side="left")
        self.is_underlined.pack(side="left")

        # ------- text
        fonttext_frame = Frame(frame_font)
        self.text_font = tkfont.Font(self, font=CONFIG.get("Widget", "font"))
        sampletitle = Label(fonttext_frame, text=_("Sample text"),
                            anchor="center", font=self.text_font,
                            style="prev.TLabel", relief="groove")

        sampletitle.grid(row=2, columnspan=2, padx=4, pady=6,
                         ipadx=4, ipady=4, sticky="eswn")
        self.fonts = list(set(tkfont.families()))
        self.fonts.append("TkDefaultFont")
        self.fonts.sort()

        self.text_font_family = StringVar(self, value=self.text_font.cget('family'))
        add_trace(self.text_font_family, 'write',
                  lambda *args: self.text_font.configure(family=self.text_font_family.get()))
        self.text_font_size = StringVar(self, value=self.text_font.cget('size'))
        add_trace(self.text_font_size, 'write',
                  lambda *args: self._config_size(self.text_font_size, self.text_font))

        w = max([len(f) for f in self.fonts])
        self.sizes = ["%i" % i for i in (list(range(6, 17)) + list(range(18, 32, 2)))]

        self.fonttext_family = AutoCompleteCombobox(fonttext_frame, values=self.fonts,
                                                    width=(w * 2) // 3,
                                                    textvariable=self.text_font_family,
                                                    exportselection=False)
        self.fonttext_family.current(self.fonts.index(self.text_font.cget('family')))
        self.fonttext_family.grid(row=0, column=0, padx=4, pady=4)
        self.fonttext_size = Combobox(fonttext_frame, values=self.sizes, width=5,
                                      exportselection=False,
                                      textvariable=self.text_font_size,
                                      validate="key",
                                      validatecommand=(self._validate_title_size, "%d", "%P", "%V"))
        self.fonttext_size.current(self.sizes.index(str(self.text_font.cget('size'))))
        self.fonttext_size.grid(row=0, column=1, padx=4, pady=4)
        # ------- grid
        frame_font.columnconfigure(1, weight=1)
        Label(frame_font,
              text=_('Title')).grid(row=0, column=0, sticky='nw', padx=4, pady=4)
        fonttitle_frame.grid(row=0, column=1)
        Label(frame_font,
              text=_('Text')).grid(row=1, column=0, sticky='nw', padx=4, pady=4)
        fonttext_frame.grid(row=1, column=1)

        # --- opacity
        opacity_frame = Frame(frame_widget)
        opacity_frame.columnconfigure(1, weight=1)
        self.opacity_scale = Scale(opacity_frame, orient="horizontal", length=300,
                                   from_=0, to=100,
                                   value=CONFIG.get("Widget", "alpha"),
                                   command=self.display_label)
        self.opacity_label = Label(opacity_frame,
                                   text="{val}%".format(val=self.opacity_scale.get()))
        Label(opacity_frame, font='TkDefaultFont 9 bold',
              text=_("Opacity")).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.opacity_scale.grid(row=0, column=1, padx=(4, 50), pady=4)
        self.opacity_label.place(in_=self.opacity_scale, relx=1, rely=0.5,
                                 anchor="w", bordermode="outside")

        # --- colors
        frame_color = Frame(frame_widget)
        frame_color.columnconfigure(1, weight=1)
        frame_color.columnconfigure(3, weight=1)
        self.entry_bg = Entry(frame_color, width=9, justify='center')
        self.entry_fg = Entry(frame_color, width=9, justify='center')
        self.entry_feed_bg = Entry(frame_color, width=9, justify='center')
        self.entry_feed_fg = Entry(frame_color, width=9, justify='center')
        self.entry_link = Entry(frame_color, width=9, justify='center')
        Label(frame_color,
              text=_('General')).grid(row=0, column=0, sticky='w', padx=4, pady=4)
        Label(frame_color, text=_('Background color')).grid(row=0, column=1,
                                                            sticky='e', padx=4,
                                                            pady=4)
        Label(frame_color, text=_('Foreground color')).grid(row=1, column=1,
                                                            sticky='e', padx=4,
                                                            pady=4)
        Label(frame_color,
              text=_('Feed entry')).grid(row=2, column=0, sticky='w', padx=4, pady=4)
        Label(frame_color, text=_('Background color')).grid(row=2, column=1,
                                                            sticky='e', padx=4,
                                                            pady=4)
        Label(frame_color, text=_('Foreground color')).grid(row=3, column=1,
                                                            sticky='e', padx=4,
                                                            pady=4)
        Label(frame_color, text=_('Link color')).grid(row=4, column=1,
                                                      sticky='e', padx=4,
                                                      pady=4)
        self.entry_bg.grid(row=0, column=2, sticky='w', padx=4, pady=4)
        self.entry_fg.grid(row=1, column=2, sticky='w', padx=4, pady=4)
        self.entry_feed_bg.grid(row=2, column=2, sticky='w', padx=4, pady=4)
        self.entry_feed_fg.grid(row=3, column=2, sticky='w', padx=4, pady=4)
        self.entry_link.grid(row=4, column=2, sticky='w', padx=4, pady=4)
        self.entry_bg.insert(0, CONFIG.get("Widget", "background"))
        self.entry_feed_fg.insert(0, CONFIG.get("Widget", "feed_foreground", fallback='white'))
        self.entry_feed_bg.insert(0, CONFIG.get("Widget", "feed_background", fallback='gray20'))
        self.entry_fg.insert(0, CONFIG.get("Widget", "foreground"))
        self.entry_link.insert(0, CONFIG.get("Widget", "link_color"))
        Button(frame_color, image=self.img_color, padding=0,
               command=lambda: self.askcolor(self.entry_bg)).grid(row=0, column=3,
                                                                  sticky='w',
                                                                  padx=4, pady=4)
        Button(frame_color, image=self.img_color, padding=0,
               command=lambda: self.askcolor(self.entry_fg)).grid(row=1, column=3,
                                                                  sticky='w',
                                                                  padx=4, pady=4)
        Button(frame_color, image=self.img_color, padding=0,
               command=lambda: self.askcolor(self.entry_feed_bg)).grid(row=2, column=3,
                                                                       sticky='w',
                                                                       padx=4, pady=4)
        Button(frame_color, image=self.img_color, padding=0,
               command=lambda: self.askcolor(self.entry_feed_fg)).grid(row=3, column=3,
                                                                       sticky='w',
                                                                       padx=4, pady=4)
        Button(frame_color, image=self.img_color, padding=0,
               command=lambda: self.askcolor(self.entry_link)).grid(row=4, column=3,
                                                                    sticky='w',
                                                                    padx=4, pady=4)

        # --- pack
        Label(frame_widget, text=_('Font'),
              font='TkDefaultFont 9 bold', anchor='w').pack(padx=4, fill='x')
        frame_font.pack(fill='x')
        Separator(frame_widget, orient='horizontal').pack(fill='x', pady=6)
        opacity_frame.pack(fill='x')
        Separator(frame_widget, orient='horizontal').pack(fill='x', pady=6)
        Label(frame_widget, text=_('Colors'),
              font='TkDefaultFont 9 bold', anchor='w').pack(padx=4, fill='x')
        frame_color.pack(fill='x')

    def askcolor(self, entry):
        try:
            color = askcolor(entry.get(), parent=self, title=_('Color'))
        except TclError:
            color = askcolor(parent=self, title=_('Color'))
        if color is not None:
            entry.delete(0, 'end')
            entry.insert(0, color)

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

    def _validate_font_size(self, combo, d, ch, V):
        """Validation of the size entry content."""
        if d == '1':
            l = [i for i in self.sizes if i[:len(ch)] == ch]
            if l:
                i = self.sizes.index(l[0])
                combo.current(i)
                index = combo.index("insert")
                combo.selection_range(index + 1, "end")
                combo.icursor(index + 1)
            return ch.isdigit()
        else:
            return True

    def change_gui(self):
        showinfo("Information",
                 _("The GUI Toolkit setting will take effect after restarting the application"),
                 parent=self)

    def ok(self):
        # --- general
        CONFIG.set("General", "language", REV_LANGUAGES[self.lang.get()])
        CONFIG.set("General", "trayicon", self.gui.get().lower())
        CONFIG.set("General", "update_delay", "%i" % (int(self.entry_delay.get()) * 60000))
        CONFIG.set('General', 'confirm_feed_remove', str(self.confirm_feed_rem.instate(('selected',))))
        CONFIG.set('General', 'confirm_cat_remove', str(self.confirm_cat_rem.instate(('selected',))))
        CONFIG.set('General', 'check_update', str(self.confirm_update.instate(('selected',))))
        # --- widget
        CONFIG.set("Widget", "alpha", "%i" % float(self.opacity_scale.get()))

        font_title_dic = self.title_font.actual()
        font_title_dic['underline'] = 'underline' if font_title_dic['underline'] else ''
        font_title_dic['family'] = font_title_dic['family'].replace(' ', '\ ')
        CONFIG.set("Widget", "font_title", "{family} {size} {weight} {slant} {underline}".format(**font_title_dic))
        font_text_dic = self.text_font.actual()
        font_text_dic['family'] = font_text_dic['family'].replace(' ', '\ ')
        CONFIG.set("Widget", "font", "{family} {size}".format(**font_text_dic))
        CONFIG.set("Widget", "foreground", self.entry_fg.get())
        CONFIG.set("Widget", "background", self.entry_bg.get())
        CONFIG.set("Widget", "feed_foreground", self.entry_feed_fg.get())
        CONFIG.set("Widget", "feed_background", self.entry_feed_bg.get())
        CONFIG.set("Widget", "link_color", self.entry_link.get())
        self.destroy()
