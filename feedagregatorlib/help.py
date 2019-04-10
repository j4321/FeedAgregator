#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

Help dialog
"""
from tkinter import Text, Toplevel
from tkinter.ttk import Button
from webbrowser import open as url_open

from PIL.ImageTk import PhotoImage

from .constants import APP_NAME, IM_ICON_24
from .autoscrollbar import AutoScrollbar


class Help(Toplevel):
    """About Toplevel."""
    def __init__(self, master):
        """Create the Toplevel 'About arxivfeed'."""
        Toplevel.__init__(self, master)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.title(_("Help"))
        self._im = PhotoImage(file=IM_ICON_24, master=self)
        text = Text(self, tabs=(2, 2), wrap="word", width=70, height=36, padx=4, pady=4)
        scroll = AutoScrollbar(self, orient='vertical', command=text.yview)
        text.tag_configure('title', font='TkDefaultFont 11 bold')
        text.tag_configure('italic', font='TkDefaultFont 9 italic')
        text.tag_configure('title2', font='TkDefaultFont 9 bold')
        text.tag_configure('list', lmargin2=20)
        text.tag_configure('email', font='TkDefaultFont 9 underline', foreground='blue')
        text.tag_configure('url', font='TkDefaultFont 9 underline', foreground='blue')
        text.tag_bind("link", "<Enter>", lambda e: text.configure(cursor='hand1'))
        text.tag_bind("link", "<Leave>", lambda e: text.configure(cursor='arrow'))
        text.tag_bind("url", "<1>", lambda e: url_open("https://github.com/j4321/FeedAgregator/issues"))
        text.tag_bind("email", "<1>", lambda e: url_open("mailto:j_4321@protonmail.com?subject=FeedAgregator"))
        text.image_create("end", image=self._im)
        text.insert("end", " {app_name}\n".format(app_name=APP_NAME), "title")
        text.insert("end",
                    _("RSS and Atom feed agregator in desktop widgets + notifications") + "\n\n",
                    "italic")
        text.insert("end",
                    _("FeedAgregator periodically looks for RSS/Atom feed updates. \
If an update is found, a notification is sent. In addition, desktop widgets \
display either all the entries of one feed or the latest entry of each \
feed of a given category.") + "\n\n")
        text.insert("end",
                    _("FeedAgregator is designed for Linux. It is written in \
Python 3 and relies mostly upon Tk GUI toolkit. The application is in the system tray, so it \
might not work with all desktop environments (see Troubleshooting).") + "\n\n\n")
        text.insert("end", _("Feed management") + "\n\n", "title2")
        text.insert("end", _("Feeds can be managed by clicking on "))
        text.insert("end", _("Manage feeds"), "italic")
        text.insert("end", _(" in the main menu (right click on the tray icon). \
A window containing the list of feeds opens:") + "\n")
        text.insert("end",
                    _("\t•\tCheck / uncheck the box on the left to activate / deactivate a feed.") + "\n",
                    'list')
        text.insert("end",
                    _("\t•\tDouble click on the feed title to edit it.") + "\n",
                    'list')
        text.insert("end",
                    _("\t•\tDouble click on the category to edit it. \
The latest entry of each feed in the same category can be displayed in a widget.") + "\n",
                    'list')
        text.insert("end",
                    _("\t•\tClick on the red minus sign on the right of a feed to delete it.") + "\n",
                    'list')
        text.insert("end",
                    _("\t•\tClick on the green plus sign to add a feed.") + "\n\n\n",
                    'list')
        text.insert("end", _("Troubleshooting") + "\n\n", "title2")
        text.insert("end",
                    _("Several GUI toolkits are available to display the system tray icon, \
so if the icon does not behave properly, try to change toolkit, they are not all fully \
compatible with every desktop environment.") + "\n\n")
        text.insert("end",
                    _("If the widgets disappear when you click on them, open the setting dialog from the menu and check the box 'Check this box if the widgets disappear when you click'.") + "\n\n")
        text.insert("end",
                    _("If you encounter bugs or if you have suggestions, please open an issue on "))
        text.insert("end", "Github", ("url", "link"))
        text.insert("end", _(" or write me an email at "))
        text.insert("end", "j_4321@protonmail.com", ("email", "link"))
        text.configure(state='disabled', yscrollcommand=scroll.set)
        text.grid(row=0, column=0, sticky='ewns')
        scroll.grid(row=0, column=1, sticky='ns')
        Button(self, text=_("Close"), command=self.exit).grid(row=1, columnspan=2,
                                                              pady=8, padx=8)

        self.protocol("WM_DELETE_WINDOW", self.exit)
        self.grab_set()

    def exit(self):
        if self.master:
            self.master.focus_set()
        self.destroy()
