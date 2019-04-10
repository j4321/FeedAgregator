#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2018-2019 Juliette Monsel <j_4321@protonmail.com>
code based on http://effbot.org/zone/tkinter-autoscrollbar.htm

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


Launch script.
"""
import os
import sys
from tkinter import Tk
from tkinter.ttk import Style
import traceback
import logging

from feedagregatorlib.messagebox import showerror
from feedagregatorlib.app import App
from feedagregatorlib.constants import PIDFILE, save_config, save_feeds, APP_NAME, save_latests


# check whether feedagregator is running
pid = str(os.getpid())

if os.path.isfile(PIDFILE):
    with open(PIDFILE) as file:
        old_pid = file.read().strip()
    if os.path.exists("/proc/%s" % old_pid):
        with open("/proc/%s/cmdline" % old_pid) as file:
            cmdline = file.read()
        if 'feedagregator' in cmdline:
            # feedagregator is already runnning
            root = Tk()
            root.withdraw()
            s = Style(root)
            s.theme_use("clam")
            logging.error("%s is already running", APP_NAME)
            showerror(_("Error"), _("{app_name} is already running, if not delete ~/.feedagregator/feedagregator.pid.").format(app_name=APP_NAME))
            sys.exit()
        else:
            # it is an old pid file
            os.remove(PIDFILE)
    else:
        # it is an old pid file
        os.remove(PIDFILE)

open(PIDFILE, 'w').write(pid)

try:
    app = App()
    app.mainloop()
except Exception as e:
    logging.exception(str(type(e)))
    showerror(_("Error"), str(type(e)), traceback.format_exc(), True)
finally:
    save_config()
    save_feeds()
    save_latests()
    os.unlink(PIDFILE)
    logging.info('Closing %s', APP_NAME)
    logging.shutdown()
