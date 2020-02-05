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


Main class
"""
import configparser
import traceback
import logging
import os
import pickle
try:
    from subprocess import run
except ImportError:
    from subprocess import call as run
from multiprocessing import Process, Queue
from datetime import datetime
from tkinter import Tk, TclError
from tkinter import PhotoImage as tkPhotoImage
from tkinter.ttk import Style

import feedparser
import dateutil.parser
from PIL.ImageTk import PhotoImage
from PIL import Image

import feedagregatorlib.constants as cst
from feedagregatorlib.messagebox import showerror
from feedagregatorlib.trayicon import TrayIcon, SubMenu
from feedagregatorlib.add import Add
from feedagregatorlib.manager import Manager
from feedagregatorlib.settings import Config
from feedagregatorlib.widgets import CatWidget, FeedWidget
from feedagregatorlib.version_check import UpdateChecker
from feedagregatorlib.about import About
from feedagregatorlib.help import Help


CONFIG = cst.CONFIG
FEEDS = cst.FEEDS
LATESTS = cst.LATESTS


class App(Tk):
    def __init__(self):
        Tk.__init__(self, className=cst.APP_NAME)
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.withdraw()

        logging.info('Starting %s', cst.APP_NAME)

        self.im_icon = PhotoImage(master=self, file=cst.IM_ICON_48)
        self.iconphoto(True, self.im_icon)

        # --- style
        self.style = Style(self)
        self.style.theme_use("clam")
        self.style.configure("TScale", sliderlength=20)
        self.style.map("TCombobox",
                       fieldbackground=[('readonly', 'white')],
                       selectbackground=[('readonly', 'white')],
                       selectforeground=[('readonly', 'black')])
        self.style.configure("title.TLabel", font="TkDefaultFont 9 bold")
        self.style.configure("white.TLabel", background="white")
        self.style.map("white.TLabel", background=[("active", "white")])
        self.style.configure('heading.TLabel', relief='ridge', borderwidth=1,
                             padding=(10, 4))
        self.style.configure('manager.TButton', padding=0)
        self.style.map('manager.Treeview', background=[], foreground=[])
        self.style.layout('no_edit.TEntry',
                          [('Entry.padding',
                            {'children': [('Entry.textarea', {'sticky': 'nswe'})],
                             'sticky': 'nswe'})])
        self.style.configure('no_edit.TEntry', background='white', padding=[4, 0])
        self.style.configure('manager.TEntry', padding=[2, 1])
        self.style.layout('manager.Treeview.Row',
                          [('Treeitem.row', {'sticky': 'nswe'}),
                           ('Treeitem.image', {'side': 'right', 'sticky': 'e'})])
        self.style.layout('manager.Treeview.Item',
                          [('Treeitem.padding',
                            {'children': [('Checkbutton.indicator',
                                           {'side': 'left', 'sticky': ''}),
                                          ('Treeitem.text', {'side': 'left', 'sticky': ''})],
                             'sticky': 'nswe'})])

        self._im_trough = tkPhotoImage(name='trough-scrollbar-vert',
                                       width=15, height=15,
                                       master=self)
        bg = CONFIG.get("Widget", 'background', fallback='gray10')
        widget_bg = (0, 0, 0)
        widget_fg = (255, 255, 255)
        vmax = self.winfo_rgb('white')[0]
        color = tuple(int(val / vmax * 255) for val in widget_bg)
        active_bg = cst.active_color(color)
        active_bg2 = cst.active_color(cst.active_color(color, 'RGB'))
        slider_vert_insens = Image.new('RGBA', (13, 28), widget_bg)
        slider_vert = Image.new('RGBA', (13, 28), active_bg)
        slider_vert_active = Image.new('RGBA', (13, 28), widget_fg)
        slider_vert_prelight = Image.new('RGBA', (13, 28), active_bg2)
        self._im_trough.put(" ".join(["{" + " ".join([bg] * 15) + "}"] * 15))
        self._im_slider_vert_active = PhotoImage(slider_vert_active,
                                                 name='slider-vert-active',
                                                 master=self)
        self._im_slider_vert = PhotoImage(slider_vert,
                                          name='slider-vert',
                                          master=self)
        self._im_slider_vert_prelight = PhotoImage(slider_vert_prelight,
                                                   name='slider-vert-prelight',
                                                   master=self)
        self._im_slider_vert_insens = PhotoImage(slider_vert_insens,
                                                 name='slider-vert-insens',
                                                 master=self)
        self.style.element_create('widget.Vertical.Scrollbar.trough', 'image',
                                  'trough-scrollbar-vert')
        self.style.element_create('widget.Vertical.Scrollbar.thumb', 'image',
                                  'slider-vert',
                                  ('pressed', '!disabled', 'slider-vert-active'),
                                  ('active', '!disabled', 'slider-vert-prelight'),
                                  ('disabled', 'slider-vert-insens'), border=6,
                                  sticky='ns')
        self.style.layout('widget.Vertical.TScrollbar',
                          [('widget.Vertical.Scrollbar.trough',
                            {'children': [('widget.Vertical.Scrollbar.thumb', {'expand': '1'})],
                             'sticky': 'ns'})])

        hide = Image.new('RGBA', (12, 12), active_bg2)
        hide_active = Image.new('RGBA', (12, 12), widget_fg)
        hide_pressed = Image.new('RGBA', (12, 12), (150, 0, 0))
        toggle_open = Image.new('RGBA', (9, 9), widget_fg)
        toggle_open_active = Image.new('RGBA', (9, 9), active_bg2)
        toggle_close = Image.new('RGBA', (9, 9), widget_fg)
        toggle_close_active = Image.new('RGBA', (9, 9), active_bg2)
        self._im_hide = PhotoImage(hide, master=self)
        self._im_hide_active = PhotoImage(hide_active, master=self)
        self._im_hide_pressed = PhotoImage(hide_pressed, master=self)
        self._im_open = PhotoImage(toggle_open, master=self)
        self._im_open_active = PhotoImage(toggle_open_active, master=self)
        self._im_close = PhotoImage(toggle_close, master=self)
        self._im_close_active = PhotoImage(toggle_close_active, master=self)

        self.style.element_create("toggle", "image", self._im_close,
                                  ("!hover", "selected", "!disabled", self._im_open),
                                  ("hover", "!selected", "!disabled", self._im_close_active),
                                  ("hover", "selected", "!disabled", self._im_open_active),
                                  border=2, sticky='')
        self.style.layout('Toggle',
                          [('Toggle.border',
                            {'children': [('Toggle.padding',
                                           {'children': [('Toggle.toggle',
                                                          {'sticky': 'nswe'})],
                                            'sticky': 'nswe'})],
                             'sticky': 'nswe'})])
        self.style.configure('widget.close.TButton', background=bg,
                             relief='flat', image=self._im_hide, padding=0)
        self.style.map('widget.close.TButton', background=[], relief=[],
                       image=[('active', '!pressed', self._im_hide_active),
                              ('active', 'pressed', self._im_hide_pressed)])
        self.option_add('*Toplevel.background', self.style.lookup('TFrame', 'background'))
        self.option_add('*{app_name}.background'.format(app_name=cst.APP_NAME), self.style.lookup('TFrame', 'background'))
        self.widget_style_init()

        # --- tray icon menu
        self.icon = TrayIcon(cst.ICON)
        self.menu_widgets = SubMenu(parent=self.icon.menu)

        self.menu_categories = SubMenu(parent=self.menu_widgets)
        self.menu_categories.add_command(label=_('Hide all'), command=self.hide_all_cats)
        self.menu_categories.add_command(label=_('Show all'), command=self.hide_all_cats)
        self.menu_categories.add_separator()

        self.menu_feeds = SubMenu(parent=self.menu_widgets)
        self.menu_feeds.add_command(label=_('Hide all'), command=self.hide_all_feeds)
        self.menu_feeds.add_command(label=_('Show all'), command=self.show_all_feeds)
        self.menu_feeds.add_separator()

        self.menu_widgets.add_command(label=_('Hide all'), command=self.hide_all)
        self.menu_widgets.add_command(label=_('Show all'), command=self.show_all)
        self.menu_widgets.add_separator()
        self.menu_widgets.add_cascade(label=_('Categories'), menu=self.menu_categories)
        self.menu_widgets.add_cascade(label=_('Feeds'), menu=self.menu_feeds)

        self.icon.menu.add_cascade(label=_('Widgets'), menu=self.menu_widgets)
        self.icon.menu.add_command(label=_('Add feed'), command=self.add)
        self.icon.menu.add_command(label=_('Update feeds'), command=self.feed_update)
        self.icon.menu.add_command(label=_('Manage feeds'),
                                   command=self.feed_manage)
        self.icon.menu.add_command(label=_("Suspend"), command=self.start_stop)
        self.icon.menu.add_separator()
        self.icon.menu.add_command(label=_('Settings'), command=self.settings)
        self.icon.menu.add_command(label=_("Check for updates"),
                                   command=lambda: UpdateChecker(self, True))
        self.icon.menu.add_command(label=_("Help"), command=lambda: Help(self))
        self.icon.menu.add_command(label=_("About"), command=lambda: About(self))
        self.icon.menu.add_command(label=_('Quit'), command=self.quit)
        self.icon.loop(self)

        self._notify_no_internet = True

        self._internet_id = ""
        self._update_id = ""
        self._check_add_id = ""
        self._check_end_update_id = ""
        self._check_result_update_id = {}
        self._check_result_init_id = {}
        self.queues = {}
        self.threads = {}

        # --- category widgets
        self.cat_widgets = {}
        self.cat_widgets['All'] = CatWidget(self, 'All')
        self.cat_widgets['All'].event_generate('<Configure>')
        self.menu_widgets.add_checkbutton(label=_('Latests'),
                                          command=self.toggle_latests_widget)
        cst.add_trace(self.cat_widgets['All'].variable, 'write',
                      self.latests_widget_trace)
        self.cat_widgets['All'].variable.set(LATESTS.getboolean('All', 'visible'))
        cats = LATESTS.sections()

        cats.remove('All')
        for category in cats:
            self.cat_widgets[category] = CatWidget(self, category)
            self.cat_widgets[category].event_generate('<Configure>')
            self.menu_categories.add_checkbutton(label=category,
                                                 command=lambda c=category: self.toggle_category_widget(c))
            cst.add_trace(self.cat_widgets[category].variable, 'write',
                          lambda *args, c=category: self.cat_widget_trace(c))
            self.cat_widgets[category].variable.set(LATESTS.getboolean(category, 'visible'))

        # --- feed widgets
        self.feed_widgets = {}
        for title in FEEDS.sections():
            self._check_result_update_id[title] = ''
            self._check_result_init_id[title] = ''
            self.queues[title] = Queue(1)
            self.threads[title] = None
            self.menu_feeds.add_checkbutton(label=title,
                                            command=lambda t=title: self.toggle_feed_widget(t))
            self.feed_widgets[title] = FeedWidget(self, title)
            cst.add_trace(self.feed_widgets[title].variable, 'write',
                          lambda *args, t=title: self.feed_widget_trace(t))
            self.feed_widgets[title].variable.set(FEEDS.getboolean(title, 'visible', fallback=True))
        self.feed_init()

        # --- check for updates
        if CONFIG.getboolean("General", "check_update"):
            UpdateChecker(self)

        self.bind_class('TEntry', '<Control-a>', self.entry_select_all)

    def report_callback_exception(self, *args):
        """Log exceptions."""
        err = "".join(traceback.format_exception(*args))
        logging.error(err)
        if args[0] is not KeyboardInterrupt:
            showerror(_("Error"), str(args[1]), err, True)
        else:
            self.quit()

    def widget_style_init(self):
        """Init widgets style."""
        bg = CONFIG.get('Widget', 'background', fallback='gray10')
        feed_bg = CONFIG.get('Widget', 'feed_background', fallback='gray20')
        fg = CONFIG.get('Widget', 'foreground')
        vmax = self.winfo_rgb('white')[0]
        widget_bg = tuple(int(val / vmax * 255) for val in self.winfo_rgb(bg))
        widget_fg = tuple(int(val / vmax * 255) for val in self.winfo_rgb(fg))
        active_bg = cst.active_color(widget_bg)
        active_bg2 = cst.active_color(cst.active_color(widget_bg, 'RGB'))
        slider_alpha = Image.open(cst.IM_SCROLL_ALPHA)
        slider_vert_insens = Image.new('RGBA', (13, 28), widget_bg)
        slider_vert = Image.new('RGBA', (13, 28), active_bg)
        slider_vert.putalpha(slider_alpha)
        slider_vert_active = Image.new('RGBA', (13, 28), widget_fg)
        slider_vert_active.putalpha(slider_alpha)
        slider_vert_prelight = Image.new('RGBA', (13, 28), active_bg2)
        slider_vert_prelight.putalpha(slider_alpha)

        self._im_slider_vert_active.paste(slider_vert_active)
        self._im_slider_vert.paste(slider_vert)
        self._im_slider_vert_prelight.paste(slider_vert_prelight)
        self._im_slider_vert_insens.paste(slider_vert_insens)
        self._im_trough.put(" ".join(["{" + " ".join([bg] * 15) + "}"] * 15))

        hide_alpha = Image.open(cst.IM_HIDE_ALPHA)
        hide = Image.new('RGBA', (12, 12), active_bg)
        hide.putalpha(hide_alpha)
        hide_active = Image.new('RGBA', (12, 12), active_bg2)
        hide_active.putalpha(hide_alpha)
        hide_pressed = Image.new('RGBA', (12, 12), widget_fg)
        hide_pressed.putalpha(hide_alpha)
        toggle_open_alpha = Image.open(cst.IM_OPENED_ALPHA)
        toggle_open = Image.new('RGBA', (9, 9), widget_fg)
        toggle_open.putalpha(toggle_open_alpha)
        toggle_open_active = Image.new('RGBA', (9, 9), active_bg2)
        toggle_open_active.putalpha(toggle_open_alpha)
        toggle_close_alpha = Image.open(cst.IM_CLOSED_ALPHA)
        toggle_close = Image.new('RGBA', (9, 9), widget_fg)
        toggle_close.putalpha(toggle_close_alpha)
        toggle_close_active = Image.new('RGBA', (9, 9), active_bg2)
        toggle_close_active.putalpha(toggle_close_alpha)
        self._im_hide.paste(hide)
        self._im_hide_active.paste(hide_active)
        self._im_hide_pressed.paste(hide_pressed)
        self._im_open.paste(toggle_open)
        self._im_open_active.paste(toggle_open_active)
        self._im_close.paste(toggle_close)
        self._im_close_active.paste(toggle_close_active)

        self.style.configure('widget.TFrame', background=bg)
        self.style.configure('widget.close.TButton', background=bg)
#                             relief='flat', image=self._im_hide, padding=0)
#        self.style.map('widget.close.TButton', background=[], relief=[],
#                       image=[('active', '!pressed', self._im_hide_active),
#                              ('active', 'pressed', self._im_hide_pressed)])
        self.style.configure('widget.interior.TFrame',
                             background=feed_bg)
        self.style.configure('widget.TSizegrip', background=bg)
        self.style.configure('widget.Horizontal.TSeparator', background=bg)
        self.style.configure('widget.TLabel', background=bg,
                             foreground=fg, font=CONFIG.get('Widget', 'font'))
        self.style.configure('widget.title.TLabel', background=bg, foreground=fg,
                             font=CONFIG.get('Widget', 'font_title'))
        self.style.configure('widget.TButton', background=bg, foreground=fg,
                             padding=1, relief='flat')
        self.style.map('widget.TButton', background=[('disabled', active_bg),
                                                     ('pressed', fg),
                                                     ('active', active_bg)],
                       foreground=[('pressed', bg)])
#                       relief=[('pressed', 'sunken')])
#                       bordercolor=[('pressed', active_bg)],
#                       darkcolor=[('pressed', bg)],
#                       lightcolor=[('pressed', fg)])

        self.update_idletasks()

    @staticmethod
    def entry_select_all(event):
        event.widget.selection_clear()
        event.widget.selection_range(0, 'end')

    def test_connection(self):
        """
        Launch update check if there is an internet connection otherwise
        check again for an internet connection after 30s.
        """
        if cst.internet_on():
            logging.info('Connected to Internet')
            self._notify_no_internet = True
            for widget in self.feed_widgets.values():
                widget.clear()
            self.feed_init()
        else:
            self._internet_id = self.after(30000, self.test_connection)

    def start_stop(self):
        """Suspend / restart update checks."""
        if self.icon.menu.get_item_label(4) == _("Suspend"):
            after_ids = [self._update_id, self._check_add_id, self._internet_id,
                         self._check_end_update_id, self._update_id]
            after_ids.extend(self._check_result_update_id.values())
            after_ids.extend(self._check_result_init_id.values())
            for after_id in after_ids:
                try:
                    self.after_cancel(after_id)
                except ValueError:
                    pass
            self.icon.menu.set_item_label(4, _("Restart"))
            self.icon.menu.disable_item(1)
            self.icon.menu.disable_item(2)
            self.icon.change_icon(cst.ICON_DISABLED, 'feedagregator suspended')
        else:
            self.icon.menu.set_item_label(4, _("Suspend"))
            self.icon.menu.enable_item(1)
            self.icon.menu.enable_item(2)
            self.icon.change_icon(cst.ICON, 'feedagregator')
            for widget in self.feed_widgets.values():
                widget.clear()
            self.feed_init()

    def settings(self):
        update_delay = CONFIG.get('General', 'update_delay')
        splash_supp = CONFIG.get('General', 'splash_supported', fallback=True)
        dialog = Config(self)
        self.wait_window(dialog)
        cst.save_config()
        self.widget_style_init()
        splash_change = splash_supp != CONFIG.get('General', 'splash_supported')
        for widget in self.cat_widgets.values():
            widget.update_style()
            if splash_change:
                widget.update_position()
        for widget in self.feed_widgets.values():
            widget.update_style()
            if splash_change:
                widget.update_position()
        if update_delay != CONFIG.get('General', 'update_delay'):
            self.feed_update()

    def add(self):
        dialog = Add(self)
        self.wait_window(dialog)
        url = dialog.url
        self.feed_add(url)

    def quit(self):
        for after_id in self.tk.call('after', 'info'):
            try:
                self.after_cancel(after_id)
            except ValueError:
                pass
        for thread in self.threads.values():
            try:
                thread.terminate()
            except AttributeError:
                pass
        for title, widget in self.feed_widgets.items():
            FEEDS.set(title, 'visible', str(widget.variable.get()))
        for cat, widget in self.cat_widgets.items():
            LATESTS.set(cat, 'visible', str(widget.variable.get()))
        try:
            self.destroy()
        except TclError:
            logging.error("Error on quit")
            self.after(500, self.quit)

    # --- hide / show
    def hide_all(self):
        """Withdraw all widgets."""
        for widget in self.cat_widgets.values():
            widget.withdraw()
        for widget in self.feed_widgets.values():
            widget.withdraw()

    def show_all(self):
        """Deiconify all widgets."""
        for widget in self.cat_widgets.values():
            widget.deiconify()
        for widget in self.feed_widgets.values():
            widget.deiconify()

    def hide_all_feeds(self):
        """Withdraw all feed widgets."""
        for widget in self.feed_widgets.values():
            widget.withdraw()

    def show_all_feeds(self):
        """Deiconify all feed widgets."""
        for widget in self.feed_widgets.values():
            widget.deiconify()

    def hide_all_cats(self):
        """Withdraw all category widgets."""
        for cat, widget in self.cat_widgets.items():
            if cat != 'All':
                widget.withdraw()

    def show_all_cats(self):
        """Deiconify all category widgets."""
        for cat, widget in self.cat_widgets.items():
            if cat != 'All':
                widget.deiconify()

    # --- visibility trace
    def feed_widget_trace(self, title):
        value = self.feed_widgets[title].variable.get()
        self.menu_feeds.set_item_value(title, value)
        FEEDS.set(title, 'visible', str(value))
        cst.save_feeds()

    def cat_widget_trace(self, category):
        value = self.cat_widgets[category].variable.get()
        self.menu_categories.set_item_value(category, value)
        LATESTS.set(category, 'visible', str(value))
        cst.save_latests()

    def latests_widget_trace(self, *args):
        value = self.cat_widgets['All'].variable.get()
        self.menu_widgets.set_item_value(_('Latests'), value)
        LATESTS.set('All', 'visible', str(value))
        cst.save_latests()

    # --- toggle visibility
    def toggle_category_widget(self, category):
        value = self.menu_categories.get_item_value(category)
        if value:
            self.cat_widgets[category].deiconify()
        else:
            self.cat_widgets[category].withdraw()
        self.update_idletasks()

    def toggle_latests_widget(self):
        value = self.menu_widgets.get_item_value(_('Latests'))
        if value:
            self.cat_widgets['All'].deiconify()
        else:
            self.cat_widgets['All'].withdraw()
        self.update_idletasks()

    def toggle_feed_widget(self, title):
        value = self.menu_feeds.get_item_value(title)
        if value:
            self.feed_widgets[title].deiconify()
        else:
            self.feed_widgets[title].withdraw()
        self.update_idletasks()

    # --- categories
    def category_remove(self, category):
        self.cat_widgets[category].destroy()
        del self.cat_widgets[category]
        self.menu_categories.delete(category)
        LATESTS.remove_section(category)
        cst.save_feeds()
        cst.save_latests()

    # --- feeds
    @staticmethod
    def feed_get_info(url, queue, mode='latest'):
        feed = feedparser.parse(url)
        feed_title = feed['feed'].get('title', '')
        entries = feed['entries']
        today = datetime.now().strftime('%Y-%m-%d %H:%M')
        if entries:
            entry_title = entries[0].get('title', '')
            summary = entries[0].get('summary', '')
            link = entries[0].get('link', '')
            latest = """<p id=title>{}</p>\n{}""".format(entry_title, summary)
            if 'updated' in entries[0]:
                updated = entries[0].get('updated')
            else:
                updated = entries[0].get('published', today)
            updated = dateutil.parser.parse(updated, tzinfos=cst.TZINFOS).strftime('%Y-%m-%d %H:%M')
        else:
            entry_title = ""
            summary = ""
            link = ""
            latest = ""
            updated = today

        if mode == 'all':
            data = []
            for entry in entries:
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                if 'updated' in entry:
                    date = entry.get('updated')
                else:
                    date = entry.get('published', today)
                date = dateutil.parser.parse(date, tzinfos=cst.TZINFOS).strftime('%Y-%m-%d %H:%M')
                data.append((title, date, summary, entry.get('link', '')))
            queue.put((feed_title, latest, updated, data, link))
        else:
            queue.put((feed_title, latest, updated, entry_title, summary, link))

    def feed_add(self, url, manager=False):
        """
        Add feed with given url.

        manager: whether this command is run from the feed manager.
        """
        if url:
            queue = Queue(1)
            manager_queue = Queue(1) if manager else None
            thread = Process(target=self.feed_get_info, args=(url, queue, 'all'),
                             daemon=True)
            thread.start()
            self._check_result_add(thread, queue, url, manager_queue)
            if manager:
                return manager_queue

    def feed_set_active(self, title, active):
        FEEDS.set(title, 'active', str(active))
        cst.save_feeds()
        cat = FEEDS.get(title, 'category', fallback='')
        if active:
            self.menu_feeds.enable_item(title)
            if FEEDS.getboolean(title, 'visible'):
                self.feed_widgets[title].deiconify()
            if cat != '':
                self.cat_widgets[cat].show_feed(title)
            self.cat_widgets['All'].show_feed(title)
            self._feed_update(title)
        else:
            self.menu_feeds.disable_item(title)
            self.feed_widgets[title].withdraw()
            if cat != '':
                self.cat_widgets[cat].hide_feed(title)
            self.cat_widgets['All'].hide_feed(title)

    def feed_change_cat(self, title, old_cat, new_cat):
        if old_cat != new_cat:
            FEEDS.set(title, 'category', new_cat)
            if old_cat != '':
                self.cat_widgets[old_cat].remove_feed(title)
            if new_cat != '':
                if new_cat not in LATESTS.sections():
                    LATESTS.add_section(new_cat)
                    LATESTS.set(new_cat, 'visible', 'True')
                    LATESTS.set(new_cat, 'geometry', '')
                    LATESTS.set(new_cat, 'position', 'normal')
                    LATESTS.set(new_cat, 'sort_order', 'A-Z')
                    self.cat_widgets[new_cat] = CatWidget(self, new_cat)
                    self.cat_widgets[new_cat].event_generate('<Configure>')
                    self.menu_categories.add_checkbutton(label=new_cat,
                                                         command=lambda: self.toggle_category_widget(new_cat))
                    cst.add_trace(self.cat_widgets[new_cat].variable, 'write',
                                  lambda *args: self.cat_widget_trace(new_cat))
                    self.cat_widgets[new_cat].variable.set(True)
                else:
                    try:
                        filename = FEEDS.get(title, 'data')
                        latest_data = cst.feed_get_latest(filename)
                    except (configparser.NoOptionError, pickle.UnpicklingError):
                        latest = ''
                        link = FEEDS.get(title, 'url')
                    else:
                        try:
                            latest, link = latest_data
                        except ValueError:  # old data
                            latest, data = cst.load_data(filename)
                            link = data[0][-1]
                    self.cat_widgets[new_cat].entry_add(title,
                                                        FEEDS.get(title, 'updated'),
                                                        latest, link)

    def feed_rename(self, old_name, new_name):
        options = {opt: FEEDS.get(old_name, opt) for opt in FEEDS.options(old_name)}
        FEEDS.remove_section(old_name)
        try:
            # check if feed's title already exists
            FEEDS.add_section(new_name)
        except configparser.DuplicateSectionError:
            i = 2
            duplicate = True
            while duplicate:
                # increment i until new_name~#i does not already exist
                try:
                    FEEDS.add_section("{}~#{}".format(new_name, i))
                except configparser.DuplicateSectionError:
                    i += 1
                else:
                    duplicate = False
                    name = "{}~#{}".format(new_name, i)
        else:
            name = new_name
        logging.info("Renamed feed '%s' to '%s'", old_name, name)
        for opt, val in options.items():
            FEEDS.set(name, opt, val)
        self._check_result_init_id[name] = self._check_result_init_id.pop(old_name, '')
        self._check_result_update_id[name] = self._check_result_update_id.pop(old_name, '')
        self.threads[name] = self.threads.pop(old_name, None)
        self.queues[name] = self.queues.pop(old_name)
        self.feed_widgets[name] = self.feed_widgets.pop(old_name)
        self.feed_widgets[name].rename_feed(name)
        self.cat_widgets['All'].rename_feed(old_name, name)
        category = FEEDS.get(name, 'category', fallback='')
        if category != '':
            self.cat_widgets[category].rename_feed(old_name, name)
        self.menu_feeds.delete(old_name)
        self.menu_feeds.add_checkbutton(label=name,
                                        command=lambda: self.toggle_feed_widget(name))
        trace_info = cst.info_trace(self.feed_widgets[name].variable)
        if trace_info:
            cst.remove_trace(self.feed_widgets[name].variable, 'write', trace_info[0][1])
        cst.add_trace(self.feed_widgets[name].variable, 'write',
                      lambda *args: self.feed_widget_trace(name))
        self.menu_feeds.set_item_value(name,
                                       self.feed_widgets[name].variable.get())

        cst.save_feeds()
        return name

    def feed_remove(self, title):
        self.feed_widgets[title].destroy()
        del self.queues[title]
        try:
            del self.threads[title]
        except KeyError:
            pass
        del self.feed_widgets[title]
        try:
            del self._check_result_init_id[title]
        except KeyError:
            pass
        try:
            del self._check_result_update_id[title]
        except KeyError:
            pass
        try:
            os.remove(os.path.join(cst.PATH_DATA, FEEDS.get(title, 'data')))
        except FileNotFoundError:
            pass
        self.menu_feeds.delete(title)
        logging.info("Removed feed '%s' %s", title, FEEDS.get(title, 'url'))
        category = FEEDS.get(title, 'category', fallback='')
        self.cat_widgets['All'].remove_feed(title)
        if category != '':
            self.cat_widgets[category].remove_feed(title)
        FEEDS.remove_section(title)

    def feed_manage(self):
        dialog = Manager(self)
        self.wait_window(dialog)
        self.update_idletasks()
        cst.save_latests()
        if dialog.change_made:
            cst.save_feeds()
            self.feed_update()

    def feed_init(self):
        """Update feeds."""
        for title in FEEDS.sections():
            if FEEDS.getboolean(title, 'active', fallback=True):
                logging.info("Updating feed '%s'", title)
                self.threads[title] = Process(target=self.feed_get_info,
                                              args=(FEEDS.get(title, 'url'),
                                                    self.queues[title], 'all'),
                                              daemon=True)
                self.threads[title].start()
                self._check_result_init(title)
        self._check_end_update_id = self.after(2000, self._check_end_update)

    def _feed_update(self, title):
        """Update feed with given title."""
        logging.info("Updating feed '%s'", title)
        self.threads[title] = Process(target=self.feed_get_info,
                                      args=(FEEDS.get(title, 'url'),
                                            self.queues[title]),
                                      daemon=True)
        self.threads[title].start()
        self._check_result_update(title)

    def feed_update(self):
        """Update all feeds."""
        try:
            self.after_cancel(self._update_id)
        except ValueError:
            pass
        for thread in self.threads.values():
            try:
                thread.terminate()
            except AttributeError:
                pass
        self.threads.clear()
        for title in FEEDS.sections():
            if FEEDS.getboolean(title, 'active', fallback=True):
                self._feed_update(title)
        self._check_end_update_id = self.after(2000, self._check_end_update)

    def _check_result_init(self, title):
        if self.threads[title].is_alive():
            self._check_result_init_id[title] = self.after(1000,
                                                           self._check_result_init,
                                                           title)
        else:
            t, latest, updated, data, link = self.queues[title].get()
            if not t:
                if cst.internet_on():
                    run(["notify-send", "-i", "dialog-error", _("Error"),
                         _('{url} is not a valid feed.').format(url=FEEDS.get(title, 'url'))])
                    logging.error('%s is not a valid feed.', FEEDS.get(title, 'url'))
                else:
                    if self._notify_no_internet:
                        run(["notify-send", "-i", "dialog-error", _("Error"),
                             _('No Internet connection.')])
                        logging.warning('No Internet connection')
                        self._notify_no_internet = False
                        self._internet_id = self.after(30000, self.test_connection)
                    after_ids = [self._update_id, self._check_add_id,
                                 self._check_end_update_id, self._update_id]
                    after_ids.extend(self._check_result_update_id.values())
                    after_ids.extend(self._check_result_init_id.values())
                    for after_id in after_ids:
                        try:
                            self.after_cancel(after_id)
                        except ValueError:
                            pass
            else:
                date = datetime.strptime(updated, '%Y-%m-%d %H:%M')
                if (date > datetime.strptime(FEEDS.get(title, 'updated'), '%Y-%m-%d %H:%M')
                   or not FEEDS.has_option(title, 'data')):
                    if CONFIG.getboolean("General", "notifications", fallback=True):
                        run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                             cst.html2text(latest)])
                    FEEDS.set(title, 'updated', updated)
                    category = FEEDS.get(title, 'category', fallback='')
                    self.cat_widgets['All'].update_display(title, latest, updated, link)
                    if category != '':
                        self.cat_widgets[category].update_display(title, latest, updated, link)
                    logging.info("Updated feed '%s'", title)
                    self.feed_widgets[title].clear()
                    for entry_title, date, summary, entry_link in data:
                        self.feed_widgets[title].entry_add(entry_title, date, summary, entry_link, -1)
                    logging.info("Populated widget for feed '%s'", title)
                    self.feed_widgets[title].event_generate('<Configure>')
                    self.feed_widgets[title].sort_by_date()
                    try:
                        filename = FEEDS.get(title, 'data')
                    except configparser.NoOptionError:
                        filename = cst.new_data_file()
                        FEEDS.set(title, 'data', filename)
                        cst.save_feeds()
                    cst.save_data(filename, (latest, link), data)
                else:
                    logging.info("Feed '%s' is up-to-date", title)

    def _check_result_update(self, title):
        if self.threads[title].is_alive():
            self._check_result_update_id[title] = self.after(1000,
                                                             self._check_result_update,
                                                             title)
        else:
            t, latest, updated, entry_title, summary, link = self.queues[title].get(False)
            if not t:
                if cst.internet_on():
                    run(["notify-send", "-i", "dialog-error", _("Error"),
                         _('{url} is not a valid feed.').format(url=FEEDS.get(title, 'url'))])
                    logging.error('%s is not a valid feed.', FEEDS.get(title, 'url'))
                else:
                    if self._notify_no_internet:
                        run(["notify-send", "-i", "dialog-error", _("Error"),
                             _('No Internet connection.')])
                        logging.warning('No Internet connection')
                        self._notify_no_internet = False
                        self._internet_id = self.after(30000, self.test_connection)
                    after_ids = [self._update_id, self._check_add_id,
                                 self._check_end_update_id, self._update_id]
                    after_ids.extend(self._check_result_update_id.values())
                    after_ids.extend(self._check_result_init_id.values())
                    for after_id in after_ids:
                        try:
                            self.after_cancel(after_id)
                        except ValueError:
                            pass
            else:
                date = datetime.strptime(updated, '%Y-%m-%d %H:%M')
                if date > datetime.strptime(FEEDS.get(title, 'updated'), '%Y-%m-%d %H:%M'):
                    logging.info("Updated feed '%s'", title)
                    if CONFIG.getboolean("General", "notifications", fallback=True):
                        run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                             cst.html2text(latest)])
                    FEEDS.set(title, 'updated', updated)
                    category = FEEDS.get(title, 'category', fallback='')
                    self.cat_widgets['All'].update_display(title, latest, updated, link)
                    if category != '':
                        self.cat_widgets[category].update_display(title, latest, updated, link)
                    self.feed_widgets[title].entry_add(entry_title, updated,
                                                       summary, link, 0)
                    self.feed_widgets[title].sort_by_date()
                    try:
                        filename = FEEDS.get(title, 'data')
                        old, data = cst.load_data(filename)
                    except pickle.UnpicklingError:
                        cst.save_data(filename, (latest, link), [(entry_title, updated, summary, link)])
                    except configparser.NoOptionError:
                        filename = cst.new_data_file()
                        FEEDS.set(title, 'data', filename)
                        cst.save_data(filename, (latest, link), [(entry_title, updated, summary, link)])
                    else:
                        data.insert(0, (entry_title, updated, summary, link))
                        cst.save_data(filename, (latest, link), data)
                else:
                    logging.info("Feed '%s' is up-to-date", title)

    def _check_result_add(self, thread, queue, url, manager_queue=None):
        if thread.is_alive():
            self._check_add_id = self.after(1000, self._check_result_add,
                                            thread, queue, url, manager_queue)
        else:
            title, latest, date, data, link = queue.get(False)
            if title:
                try:
                    # check if feed's title already exists
                    FEEDS.add_section(title)
                except configparser.DuplicateSectionError:
                    i = 2
                    duplicate = True
                    while duplicate:
                        # increment i until title~#i does not already exist
                        try:
                            FEEDS.add_section("{}~#{}".format(title, i))
                        except configparser.DuplicateSectionError:
                            i += 1
                        else:
                            duplicate = False
                            name = "{}~#{}".format(title, i)
                else:
                    name = title
                if manager_queue is not None:
                    manager_queue.put(name)
                logging.info("Added feed '%s' %s", name, url)
                if CONFIG.getboolean("General", "notifications", fallback=True):
                    run(["notify-send", "-i", cst.IM_ICON_SVG, name,
                         cst.html2text(latest)])
                self.cat_widgets['All'].entry_add(name, date, latest, link)
                filename = cst.new_data_file()
                cst.save_data(filename, (latest, link), data)
                FEEDS.set(name, 'url', url)
                FEEDS.set(name, 'updated', date)
                FEEDS.set(name, 'data', filename)
                FEEDS.set(name, 'visible', 'True')
                FEEDS.set(name, 'geometry', '')
                FEEDS.set(name, 'position', 'normal')
                FEEDS.set(name, 'category', '')
                FEEDS.set(name, 'sort_is_reversed', 'False')
                FEEDS.set(name, 'active', 'True')
                cst.save_feeds()
                self.queues[name] = queue
                self.feed_widgets[name] = FeedWidget(self, name)
                self.menu_feeds.add_checkbutton(label=name,
                                                command=lambda: self.toggle_feed_widget(name))
                cst.add_trace(self.feed_widgets[name].variable, 'write',
                              lambda *args: self.feed_widget_trace(name))
                self.feed_widgets[name].variable.set(True)
                for entry_title, date, summary, entry_link in data:
                    self.feed_widgets[name].entry_add(entry_title, date, summary, entry_link, -1)
            else:
                if manager_queue is not None:
                    manager_queue.put('')
                if cst.internet_on():
                    logging.error('%s is not a valid feed.', url)
                    showerror(_('Error'), _('{url} is not a valid feed.').format(url=url))
                else:
                    logging.warning('No Internet connection.')
                    showerror(_('Error'), _('No Internet connection.'))

    def _check_end_update(self):
        b = [t.is_alive() for t in self.threads.values() if t is not None]
        if sum(b):
            self._check_end_update_id = self.after(1000, self._check_end_update)
        else:
            cst.save_feeds()
            for widget in self.cat_widgets.values():
                widget.sort()
            self._update_id = self.after(CONFIG.getint("General", "update_delay"),
                                         self.feed_update)
