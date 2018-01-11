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


Main class
"""
import feedparser
import dateutil.parser
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from feedagregatorlib.messagebox import showerror
from feedagregatorlib.trayicon import TrayIcon, SubMenu
import feedagregatorlib.constants as cst
from feedagregatorlib.add import Add
from feedagregatorlib.manager import Manager
from feedagregatorlib.config import Config
from feedagregatorlib.widget import Widget
from feedagregatorlib.feed_widget import FeedWidget
from feedagregatorlib.version_check import UpdateChecker
from feedagregatorlib.about import About
from subprocess import run
import configparser
import traceback
from multiprocessing import Process, Queue


CONFIG = cst.CONFIG
FEEDS = cst.FEEDS


class App(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self, className=cst.APP_NAME)
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.withdraw()

        self.im_icon = cst.PhotoImage(master=self, file=cst.IM_ICON_48)
        self.iconphoto(True, self.im_icon)

        # --- style
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TScale", sliderlength=20)
        self.style.map("TCombobox",
                       fieldbackground=[('readonly', 'white')],
                       selectbackground=[('readonly', 'white')],
                       selectforeground=[('readonly', 'black')])
        self.style.configure("prev.TLabel", background="white")
        self.style.map("prev.TLabel", background=[("active", "white")])
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
        self.widget_style_init()

        # --- tray icon menu
        self.icon = TrayIcon(cst.ICON)
        self.menu_widgets = SubMenu(parent=self.icon.menu)
        self.menu_widgets.add_command(label=_('Hide all'), command=self.hide_all)
        self.menu_widgets.add_command(label=_('Show all'), command=self.show_all)
        self.menu_widgets.add_checkbutton(label=_("Latests"),
                                          command=self.toggle_widget)
        self.icon.menu.add_cascade(label=_('Widgets'), menu=self.menu_widgets)
        self.icon.menu.add_command(label=_('Add feed'), command=self.add)
        self.icon.menu.add_command(label=_('Manage feeds'),
                                   command=self.feed_manage)
        self.icon.menu.add_command(label=_("Suspend"), command=self.start_stop)
        self.icon.menu.add_separator()
        self.icon.menu.add_command(label=_('Settings'), command=self.settings)
        self.icon.menu.add_command(label=_("Check for updates"),
                                   command=lambda: UpdateChecker(self, True))
        self.icon.menu.add_command(label=_("About"), command=lambda: About(self))
        self.icon.menu.add_command(label=_('Quit'), command=self.quit)
        self.icon.loop(self)

        self.widget = Widget(self)
        self.menu_widgets.set_item_value(_("Latests"),
                                         bool(CONFIG.get('Widget', 'geometry')))
        cst.add_trace(self.widget.variable, 'write', self.widget_trace)

        self._notify_no_internet = True

        self._internet_id = ""
        self._update_id = ""
        self._check_add_id = ""
        self._check_end_update_id = ""
        self._check_result_update_id = {}
        self._check_result_init_id = {}
        self.queues = {}
        self.threads = {}
        self.feed_widgets = {}
        for title in FEEDS.sections():
            self._check_result_update_id[title] = ''
            self._check_result_init_id[title] = ''
            self.queues[title] = Queue(1)
            self.threads[title] = None
            self.menu_widgets.add_checkbutton(label=title,
                                              command=lambda t=title: self.toggle_feed_widget(t))
            self.feed_widgets[title] = FeedWidget(self, title)
            cst.add_trace(self.feed_widgets[title].variable, 'write',
                          lambda *args, t=title: self.feed_widget_trace(t))
        self.feed_init()

        # --- check for updates
        if CONFIG.getboolean("General", "check_update"):
            UpdateChecker(self)

        self.bind_class('TEntry', '<Control-a>', self.entry_select_all)

    def widget_style_init(self):
        """Init widgets style."""
        bg = CONFIG.get('Widget', 'background')
        fg = CONFIG.get('Widget', 'foreground')
        vmax = self.winfo_rgb('white')[0]
        color = tuple(int(val / vmax * 255) for val in self.winfo_rgb(bg))
        active_bg = cst.active_color(color)
        self.style.configure('widget.TFrame', background=bg)
        self.style.configure('widget.line.TFrame', background=active_bg)
        self.style.configure('widget.TSizegrip', background=bg)
        self.style.configure('widget.TSeparator', background=bg)
        self.style.configure('widget.TLabel', background=bg, foreground=fg)
        self.style.configure('widget.TLabel', background=bg, foreground=fg,
                             font=CONFIG.get('Widget', 'font'))
        self.style.configure('widget.title.TLabel', background=bg, foreground=fg,
                             font=CONFIG.get('Widget', 'font_title'))
        self.style.configure('widget.TButton', background=bg, foreground=fg,
                             padding=1, darkcolor=active_bg, lightcolor=active_bg,
                             bordercolor=active_bg)
        self.style.map('widget.TButton', background=[('disabled', active_bg),
                                                     ('pressed', active_bg),
                                                     ('active', active_bg)],
                       darkcolor=[('pressed', fg)],
                       lightcolor=[('pressed', fg)])

    def hide_all(self):
        """Withdraw all widgets."""
        self.widget.withdraw()
        for widget in self.feed_widgets.values():
            widget.withdraw()

    def show_all(self):
        """Deiconify all widgets."""
        self.widget.deiconify()
        for widget in self.feed_widgets.values():
            widget.deiconify()

    def start_stop(self):
        """Suspend / restart update checks."""
        if self.icon.menu.get_item_label(3) == _("Suspend"):
            after_ids = [self._update_id, self._check_add_id, self._internet_id,
                         self._check_end_update_id, self._update_id]
            after_ids.extend(self._check_result_update_id.values())
            after_ids.extend(self._check_result_init_id.values())
            for after_id in after_ids:
                self.after_cancel(after_id)
            self.icon.menu.set_item_label(3, _("Restart"))
            self.icon.menu.disable_item(1)
            self.icon.change_icon(cst.ICON_DISABLED, 'feedagregator suspended')
        else:
            self.icon.menu.set_item_label(3, _("Suspend"))
            self.icon.menu.enable_item(1)
            self.icon.change_icon(cst.ICON, 'feedagregator')
            for widget in self.feed_widgets.values():
                widget.clear()
            self.feed_init()

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
            self.reset_conn()
            self._notify_no_internet = True
            for widget in self.feed_widgets.values():
                widget.clear()
            self.feed_init()
        else:
            self._internet_id = self.after(30000, self.test_connection)

    def quit(self):
        after_ids = [self._update_id, self._check_add_id, self._internet_id,
                     self._check_end_update_id, self._update_id, self.loop_id]
        after_ids.extend(self._check_result_update_id.values())
        after_ids.extend(self._check_result_init_id.values())
        for after_id in after_ids:
            self.after_cancel(after_id)
        self.destroy()

    def feed_widget_trace(self, title):
        self.menu_widgets.set_item_value(title,
                                         self.feed_widgets[title].variable.get())

    def widget_trace(self, *args):
        self.menu_widgets.set_item_value(_("Latests"), self.widget.variable.get())

    def toggle_widget(self):
        value = self.menu_widgets.get_item_value(_("Latests"))
        if value:
            self.widget.deiconify()
        else:
            self.widget.withdraw()

    def toggle_feed_widget(self, title):
        value = self.menu_widgets.get_item_value(title)
        if value:
            self.feed_widgets[title].deiconify()
        else:
            self.feed_widgets[title].withdraw()

    def report_callback_exception(self, *args):
        """Log exceptions."""
        err = "".join(traceback.format_exception(*args))
        showerror(_("Error"), str(args[1]), err)

    def settings(self):
        dialog = Config(self)
        self.wait_window(dialog)
        cst.save_config()
        self.widget_style_init()
        self.widget.update_style()
        for widget in self.feed_widgets.values():
            widget.update_style()

    def add(self):
        dialog = Add(self)
        self.wait_window(dialog)
        url = dialog.url
        self.feed_add(url)

    @staticmethod
    def feed_get_info(url, queue, mode='latest'):
        feed = feedparser.parse(url)
        feed_title = feed['feed'].get('title', '')
        entries = feed['entries']
        today = datetime.now().strftime('%Y-%m-%d %H:%M')
        if entries:
            latest = """<p id=title>{}</p>\n{}""".format(entries[0].get('title', ''),
                                                                    entries[0].get('summary', ''))
            updated = dateutil.parser.parse(entries[0].get('updated', today)).strftime('%Y-%m-%d %H:%M')
        else:
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
                date = dateutil.parser.parse(date).strftime('%Y-%m-%d %H:%M')
                data.append((title, date, summary))
            queue.put((feed_title, latest, updated, data))
        else:
            queue.put((feed_title, latest, updated))

    def _check_result_add(self, thread, queue, url):
        if thread.is_alive():
            self._check_add_id = self.after(1000, self._check_result_add,
                                            thread, queue, url)
        else:
            title, latest, date, data = queue.get()
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
                run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                     cst.html2text(latest)])
                self.widget.add_feed(name, latest, url, date)
                FEEDS.set(name, 'url', url)
                FEEDS.set(name, 'visible', 'True')
                FEEDS.set(name, 'updated', date)
                FEEDS.set(name, 'latest', latest)
                FEEDS.set(name, 'geometry', '')
                FEEDS.set(name, 'position', 'normal')
                cst.save_feeds()
                self.queues[title] = queue
                self.feed_widgets[title] = FeedWidget(self, name)
                self.feed_widgets[title] = FeedWidget(self, title)
                self.menu_widgets.add_checkbutton(label=_(title),
                                                  command=lambda: self.toggle_feed_widget(title))
                cst.add_trace(self.feed_widgets[title].variable, 'write',
                              lambda *args: self.feed_widget_trace(title))
                for entry_title, date, summary in data:
                    self.feed_widgets[title].entry_add(entry_title, date, summary, -1)
            else:
                if cst.internet_on():
                    showerror(_('Error'), _('{url} is not a valid feed.').format(url=url))
                else:
                    showerror(_('Error'), _('No Internet connection.'))

    def feed_add(self, url):
        if url:
            queue = Queue(1)
            thread = Process(target=self.feed_get_info, args=(url, queue, 'all'),
                             daemon=True)
            thread.start()
            self._check_result_add(thread, queue, url)

    def feed_show(self, title):
        self.widget.show_feed(title)
        FEEDS.set(title, 'visible', 'True')

    def feed_hide(self, title):
        self.widget.hide_feed(title)
        FEEDS.set(title, 'visible', 'False')

    def feed_rename(self, old_name, new_name):
        url = FEEDS.get(old_name, 'url')
        visible = FEEDS.get(old_name, 'visible')
        latest = FEEDS.get(old_name, 'latest')
        position = FEEDS.get(old_name, 'position')
        geometry = FEEDS.get(old_name, 'geometry')
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
        FEEDS.set(name, 'url', url)
        FEEDS.set(name, 'visible', visible)
        FEEDS.set(name, 'latest', latest)
        FEEDS.set(name, 'position', position)
        FEEDS.set(name, 'geometry', geometry)
        self._check_result_init_id[name] = self._check_result_init_id.pop(old_name)
        self._check_result_update_id[name] = self._check_result_update_id.pop(old_name)
        self.threads[name] = self.threads.pop(old_name)
        self.queues[name] = self.queues.pop(old_name)
        self.feed_widgets[name] = self.feed_widgets.pop(old_name)
        self.feed_widgets[name].rename_feed(name)
        self.widget.rename_feed(old_name, name)
        self.menu_widgets.delete(old_name)
        self.menu_widgets.add_checkbutton(label=_(name),
                                          command=lambda: self.toggle_feed_widget(name))
        trace_id = cst.trinfo_trace(self.feed_widgets[name].variable)[0][1]
        cst.remove_trace(self.feed_widgets[name].variable, 'write', trace_id)
        cst.add_trace(self.feed_widgets[name].variable, 'write',
                      lambda *args: self.feed_widget_trace(name))
        cst.save_feeds()
        return name

    def feed_remove(self, title):
        try:
            self.feed_widgets[title].destroy()
            del self.queues[title]
            del self.threads[title]
            del self.feed_widgets[title]
            del self._check_result_init_id[title]
            del self._check_result_update_id[title]
            self.menu_widgets.delete(title)
        except KeyError:
            pass
        FEEDS.remove_section(title)
        self.widget.remove_feed(title)

    def feed_manage(self):
        dialog = Manager(self)
        self.wait_window(dialog)
        self.update_idletasks()
        if dialog.change_made:
            cst.save_feeds()
            self.feed_update()

    def feed_init(self):
        """Update feeds."""
        for title in FEEDS.sections():
            self.threads[title] = Process(target=self.feed_get_info,
                                          args=(FEEDS.get(title, 'url'),
                                                self.queues[title], 'all'),
                                          daemon=True)
            self.threads[title].start()
            self._check_result_init(title)
        self._check_end_update_id = self.after(2000, self._check_end_update)

    def _check_result_init(self, title):
        if self.threads[title].is_alive():
            self._check_result_init_id[title] = self.after(1000,
                                                           self._check_result_init,
                                                           title)
        else:
            t, latest, updated, data = self.queues[title].get()
            if not t:
                if cst.internet_on():
                    run(["notify-send", "-i", "dialog-error", _("Error"),
                         _('{url} is not a valid feed.').format(url=FEEDS.get(title, 'url'))])
                else:
                    if self._notify_no_internet:
                        run(["notify-send", "-i", "dialog-error", _("Error"),
                             _('No Internet connection.')])
                        self._notify_no_internet = False
                        self._internet_id = self.after(30000, self.test_connection)
                    after_ids = [self._update_id, self._check_add_id,
                                 self._check_end_update_id, self._update_id]
                    after_ids.extend(self._check_result_update_id.values())
                    after_ids.extend(self._check_result_init_id.values())
                    for after_id in after_ids:
                        self.after_cancel(after_id)
            else:
                date = datetime.strptime(updated, '%Y-%m-%d %H:%M')
                if date > datetime.strptime(FEEDS.get(title, 'updated'), '%Y-%m-%d %H:%M'):
                    run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                         cst.html2text(latest)])
                    FEEDS.set(title, 'latest', latest)
                    FEEDS.set(title, 'updated', updated)
                    self.widget.update_display(title, latest, updated)
                for entry_title, date, summary in data:
                    self.feed_widgets[title].entry_add(entry_title, date, summary, -1)

    def feed_update(self, terminate=True):
        """Update feeds."""
        self.after_cancel(self._update_id)
        if terminate:
            for thread in self.threads.values():
                thread.terminate()
        self.threads.clear()
        for title in FEEDS.sections():
            self.threads[title] = Process(target=self.feed_get_info,
                                          args=(FEEDS.get(title, 'url'),
                                                self.queues[title]),
                                          daemon=True)
            self.threads[title].start()
            self._check_result_update(title)
        self._check_end_update_id = self.after(2000, self._check_end_update)

    def _check_result_update(self, title):
        if self.threads[title].is_alive():
            self._check_result_update_id[title] = self.after(1000,
                                                             self._check_result_update,
                                                             title)
        else:
            t, latest, updated = self.queues[title].get()
            if not t:
                if cst.internet_on():
                    run(["notify-send", "-i", "dialog-error", _("Error"),
                         _('{url} is not a valid feed.').format(url=FEEDS.get(title, 'url'))])
                else:
                    if self._notify_no_internet:
                        run(["notify-send", "-i", "dialog-error", _("Error"),
                             _('No Internet connection.')])
                        self._notify_no_internet = False
                        self._internet_id = self.after(30000, self.test_connection)
                    after_ids = [self._update_id, self._check_add_id,
                                 self._check_end_update_id, self._update_id]
                    after_ids.extend(self._check_result_update_id.values())
                    after_ids.extend(self._check_result_init_id.values())
                    for after_id in after_ids:
                        self.after_cancel(after_id)
            else:
                date = datetime.strptime(updated, '%Y-%m-%d %H:%M')
                if date > datetime.strptime(FEEDS.get(title, 'updated'), '%Y-%m-%d %H:%M'):
                    run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                         cst.html2text(latest)])
                    FEEDS.set(title, 'latest', latest)
                    FEEDS.set(title, 'updated', updated)
                    self.widget.update_display(title, latest, updated)
                    start = latest.find('<entry_title>') + 13
                    end = latest.find('</entry_title>')
                    self.feed_widgets[title].entry_add(latest[start: end], date,
                                                       latest[end + 15:], 0)

    def _check_end_update(self):
        b = [t.is_alive() for t in self.threads.values()]
        if sum(b):
            self._check_end_update_id = self.after(1000, self._check_end_update)
        else:
            cst.save_feeds()
            self._update_id = self.after(CONFIG.getint("General", "update_delay"),
                                         self.feed_update)
