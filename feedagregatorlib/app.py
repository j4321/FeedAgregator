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
from tkinter import Tk
from tkinter.ttk import Style
from feedagregatorlib.messagebox import showerror
from feedagregatorlib.trayicon import TrayIcon, SubMenu
import feedagregatorlib.constants as cst
from feedagregatorlib.add import Add
from feedagregatorlib.manager import Manager
from feedagregatorlib.config import Config
from feedagregatorlib.cat_widget import CatWidget
from feedagregatorlib.feed_widget import FeedWidget
from feedagregatorlib.version_check import UpdateChecker
from feedagregatorlib.about import About
from subprocess import run
import configparser
import traceback
from multiprocessing import Process, Queue
import logging


CONFIG = cst.CONFIG
FEEDS = cst.FEEDS
LATESTS = cst.LATESTS


class App(Tk):
    def __init__(self):
        Tk.__init__(self, className=cst.APP_NAME)
        self.protocol("WM_DELETE_WINDOW", self.quit)
        self.withdraw()

        logging.info('Starting %s', cst.APP_NAME)

        self.im_icon = cst.PhotoImage(master=self, file=cst.IM_ICON_48)
        self.iconphoto(True, self.im_icon)

        # --- style
        self.style = Style(self)
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
        self.widget_style_init()

        # --- tray icon menu
        self.icon = TrayIcon(cst.ICON)
        self.menu_widgets = SubMenu(parent=self.icon.menu)
        self.menu_categories = SubMenu(parent=self.menu_widgets)
        self.menu_categories.add_command(label=_('Hide all'), command=self.hide_all_cats)
        self.menu_categories.add_command(label=_('Show all'), command=self.hide_all_cats)
        self.menu_feeds = SubMenu(parent=self.menu_widgets)
        self.menu_feeds.add_command(label=_('Hide all'), command=self.hide_all_feeds)
        self.menu_feeds.add_command(label=_('Show all'), command=self.show_all_feeds)

        self.menu_widgets.add_cascade(label=_('Categories'), menu=self.menu_categories)
        self.menu_widgets.add_cascade(label=_('Feeds'), menu=self.menu_feeds)
        self.menu_widgets.add_command(label=_('Hide all'), command=self.hide_all)
        self.menu_widgets.add_command(label=_('Show all'), command=self.show_all)

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

        self._notify_no_internet = True

        self._internet_id = ""
        self._update_id = ""
        self._check_add_id = ""
        self._check_end_update_id = ""
        self._check_result_update_id = {}
        self._check_result_init_id = {}
        self.queues = {}
        self.threads = {}
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
                          lambda *args, t=title: self.feed_cat_widget_trace(t))
            self.feed_widgets[title].variable.set(FEEDS.getboolean(title, 'visible'))
        self.feed_init()

        # --- check for updates
        if CONFIG.getboolean("General", "check_update"):
            UpdateChecker(self)

        self.bind_class('TEntry', '<Control-a>', self.entry_select_all)

    def widget_style_init(self):
        """Init widgets style."""
        bg = CONFIG.get('Widget', 'background')
        feed_bg = CONFIG.get('Widget', 'feed_background')
        fg = CONFIG.get('Widget', 'foreground')
        vmax = self.winfo_rgb('white')[0]
        color = tuple(int(val / vmax * 255) for val in self.winfo_rgb(bg))
        active_bg = cst.active_color(color)
        self.style.configure('widget.TFrame', background=bg)
        self.style.configure('widget.interior.TFrame',
                             background=feed_bg)
        self.style.configure('widget.TSizegrip', background=bg)
        self.style.configure('widget.TSeparator', background=bg)
        self.style.configure('widget.TLabel', background=bg,
                             foreground=fg, font=CONFIG.get('Widget', 'font'))
        self.style.configure('widget.title.TLabel', background=bg, foreground=fg,
                             font=CONFIG.get('Widget', 'font_title'))
        self.style.configure('widget.TButton', background=bg, foreground=fg,
                             padding=1, relief='flat')
        self.style.map('widget.TButton', background=[('disabled', active_bg),
                                                     ('pressed', bg),
                                                     ('active', active_bg)],
                       relief=[('pressed', 'sunken')],
                       bordercolor=[('pressed', active_bg)],
                       darkcolor=[('pressed', bg)],
                       lightcolor=[('pressed', fg)])

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
            logging.info('Connected to Internet')
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
        for thread in self.threads.values():
            try:
                thread.terminate()
            except AttributeError:
                pass
        for title, widget in self.feed_widgets.items():
            FEEDS.set(title, 'visible', str(widget.variable.get()))
        for cat, widget in self.cat_widgets.items():
            LATESTS.set(cat, 'visible', str(widget.variable.get()))
        self.destroy()

    def feed_cat_widget_trace(self, title):
        self.menu_feeds.set_item_value(title,
                                       self.feed_widgets[title].variable.get())

    def cat_widget_trace(self, category):
        self.menu_categories.set_item_value(category,
                                            self.cat_widgets[category].variable.get())

    def latests_widget_trace(self, *args):
        self.menu_widgets.set_item_value(_('Latests'),
                                         self.cat_widgets['All'].variable.get())

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

    def report_callback_exception(self, *args):
        """Log exceptions."""
        err = "".join(traceback.format_exception(*args))
        logging.error(err)
        showerror(_("Error"), str(args[1]), err, True)

    def settings(self):
        dialog = Config(self)
        self.wait_window(dialog)
        cst.save_config()
        self.widget_style_init()
        for widget in self.cat_widgets.values():
            widget.update_style()
        for widget in self.feed_widgets.values():
            widget.update_style()

    def add(self):
        dialog = Add(self)
        self.wait_window(dialog)
        url = dialog.url
        self.feed_add(url)

    def category_remove(self, category):
        self.cat_widgets[category].destroy()
        del self.cat_widgets[category]
        self.menu_categories.delete(category)
        LATESTS.remove_section(category)
        cst.save_feeds()
        cst.save_latests()

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
            updated = dateutil.parser.parse(entries[0].get('updated', today)).strftime('%Y-%m-%d %H:%M')
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
                date = dateutil.parser.parse(date).strftime('%Y-%m-%d %H:%M')
                link = entry.get('link', '')
                data.append((title, date, summary, link))
            queue.put((feed_title, latest, updated, data))
        else:
            queue.put((feed_title, latest, updated, entry_title, summary, link))

    def _check_result_add(self, thread, queue, url, manager_queue=None):
        if thread.is_alive():
            self._check_add_id = self.after(1000, self._check_result_add,
                                            thread, queue, url, manager_queue)
        else:
            title, latest, date, data = queue.get(False)
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
                run(["notify-send", "-i", cst.IM_ICON_SVG, name,
                     cst.html2text(latest)])
                self.cat_widgets['All'].add_feed(name, latest, url, date)
                FEEDS.set(name, 'url', url)
                FEEDS.set(name, 'updated', date)
                FEEDS.set(name, 'latest', latest)
                FEEDS.set(name, 'visible', 'True')
                FEEDS.set(name, 'geometry', '')
                FEEDS.set(name, 'position', 'normal')
                FEEDS.set(name, 'category', '')
                cst.save_feeds()
                self.queues[name] = queue
                self.feed_widgets[name] = FeedWidget(self, name)
                self.menu_feeds.add_checkbutton(label=name,
                                                command=lambda: self.toggle_feed_widget(name))
                cst.add_trace(self.feed_widgets[name].variable, 'write',
                              lambda *args: self.feed_cat_widget_trace(name))
                self.feed_widgets[name].variable.set(True)
                for entry_title, date, summary, link in data:
                    self.feed_widgets[name].entry_add(entry_title, date, summary, link, -1)
            else:
                if manager_queue is not None:
                    manager_queue.put('')
                if cst.internet_on():
                    logging.error('%s is not a valid feed.', url)
                    showerror(_('Error'), _('{url} is not a valid feed.').format(url=url))
                else:
                    logging.warning('No Internet connection.')
                    showerror(_('Error'), _('No Internet connection.'))

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
                    self.cat_widgets[new_cat] = CatWidget(self, new_cat)
                    self.cat_widgets[new_cat].event_generate('<Configure>')
                    self.menu_categories.add_checkbutton(label=new_cat,
                                                         command=lambda: self.toggle_category_widget(new_cat))
                    cst.add_trace(self.cat_widgets[new_cat].variable, 'write',
                                  lambda *args: self.cat_widget_trace(new_cat))
                    self.cat_widgets[new_cat].variable.set(True)
                else:
                    self.cat_widgets[new_cat].add_feed(title,
                                                       FEEDS.get(title, 'latest'),
                                                       FEEDS.get(title, 'url'),
                                                       FEEDS.get(title, 'updated'))

    def feed_rename(self, old_name, new_name):
        url = FEEDS.get(old_name, 'url')
        updated = FEEDS.get(old_name, 'updated')
        visible = FEEDS.get(old_name, 'visible')
        latest = FEEDS.get(old_name, 'latest')
        category = FEEDS.get(old_name, 'category', fallback='')
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
        logging.info("Renamed feed '%s' to '%s'", old_name, name)
        FEEDS.set(name, 'url', url)
        FEEDS.set(name, 'updated', updated)
        FEEDS.set(name, 'latest', latest)
        FEEDS.set(name, 'visible', visible)
        FEEDS.set(name, 'geometry', geometry)
        FEEDS.set(name, 'position', position)
        FEEDS.set(name, 'category', category)
        self._check_result_init_id[name] = self._check_result_init_id.pop(old_name, '')
        self._check_result_update_id[name] = self._check_result_update_id.pop(old_name, '')
        self.threads[name] = self.threads.pop(old_name, None)
        self.queues[name] = self.queues.pop(old_name)
        self.feed_widgets[name] = self.feed_widgets.pop(old_name)
        self.feed_widgets[name].rename_feed(name)
        self.cat_widgets['All'].rename_feed(old_name, name)
        if category != '':
            self.cat_widgets[category].rename_feed(old_name, name)
        self.menu_feeds.delete(old_name)
        self.menu_feeds.add_checkbutton(label=name,
                                        command=lambda: self.toggle_feed_widget(name))
        trace_info = cst.info_trace(self.feed_widgets[name].variable)
        if trace_info:
            cst.remove_trace(self.feed_widgets[name].variable, 'write', trace_info[0][1])
        cst.add_trace(self.feed_widgets[name].variable, 'write',
                      lambda *args: self.feed_cat_widget_trace(name))
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
#        cats = LATESTS.sections()
#        cats.remove('All')
#        cats.append('')
#        new_cats = [cat for cat in dialog.categories if cat not in cats]
#        for cat in new_cats:
#            LATESTS.add_section(cat)
#            LATESTS.set(cat, 'visible', 'True')
#            LATESTS.set(cat, 'geometry', '')
#            LATESTS.set(cat, 'position', 'normal')
#            self.cat_widgets[cat] = CatWidget(self, cat)
#            self.cat_widgets[cat].event_generate('<Configure>')
#            self.menu_categories.add_checkbutton(label=cat,
#                                                 command=lambda: self.toggle_category_widget(cat))
#            cst.add_trace(self.cat_widgets[cat].variable, 'write',
#                          lambda *args: self.cat_widget_trace(cat))
#            self.cat_widgets[cat].variable.set(True)
        cst.save_latests()
        if dialog.change_made:
            cst.save_feeds()
            self.feed_update()

    def feed_init(self):
        """Update feeds."""
        for title in FEEDS.sections():
            logging.info("Updating feed '%s'", title)
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
                        self.after_cancel(after_id)
            else:
                date = datetime.strptime(updated, '%Y-%m-%d %H:%M')
                if date > datetime.strptime(FEEDS.get(title, 'updated'), '%Y-%m-%d %H:%M'):
                    run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                         cst.html2text(latest)])
                    FEEDS.set(title, 'latest', latest)
                    FEEDS.set(title, 'updated', updated)
                    category = FEEDS.get(title, 'category')
                    self.cat_widgets[category].update_display(title, latest, updated)
                    if category != '':
                        self.cat_widgets[category].update_display(title, latest, updated)
                    logging.info("Updated feed '%s'", title)
                else:
                    logging.info("Feed '%s' is up-to-date", title)
                for entry_title, date, summary, link in data:
                    self.feed_widgets[title].entry_add(entry_title, date, summary, link, -1)
                logging.info("Populated widget for feed '%s'", title)
                self.feed_widgets[title].event_generate('<Configure>')

    def feed_update(self):
        """Update feeds."""
        self.after_cancel(self._update_id)
        for thread in self.threads.values():
            try:
                thread.terminate()
            except AttributeError:
                pass
        self.threads.clear()
        for title in FEEDS.sections():
            logging.info("Updating feed '%s'", title)
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
                        self.after_cancel(after_id)
            else:
                date = datetime.strptime(updated, '%Y-%m-%d %H:%M')
                if date > datetime.strptime(FEEDS.get(title, 'updated'), '%Y-%m-%d %H:%M'):
                    logging.info("Updated feed '%s'", title)
                    run(["notify-send", "-i", cst.IM_ICON_SVG, title,
                         cst.html2text(latest)])
                    FEEDS.set(title, 'latest', latest)
                    FEEDS.set(title, 'updated', updated)
                    category = FEEDS.get(title, 'category')
                    self.cat_widgets['All'].update_display(title, latest, updated)
                    if category != '':
                        self.cat_widgets[category].update_display(title, latest, updated)
                    self.feed_widgets[title].entry_add(entry_title, updated,
                                                       summary, link, 0)
                else:
                    logging.info("Feed '%s' is up-to-date", title)

    def _check_end_update(self):
        b = [t.is_alive() for t in self.threads.values()]
        if sum(b):
            self._check_end_update_id = self.after(1000, self._check_end_update)
        else:
            cst.save_feeds()
            self._update_id = self.after(CONFIG.getint("General", "update_delay"),
                                         self.feed_update)
