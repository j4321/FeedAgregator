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


The images in ICONS were taken from "icons.tcl":

    A set of stock icons for use in Tk dialogs. The icons used here
    were provided by the Tango Desktop project which provides a
    unified set of high quality icons licensed under the
    Creative Commons Attribution Share-Alike license
    (http://creativecommons.org/licenses/by-sa/3.0/)

    See http://tango.freedesktop.org/Tango_Desktop_Project

    Copyright (c) 2009 Pat Thoyts <patthoyts@users.sourceforge.net>

The scroll.png image is a modified version of the slider-vert.png assets from
the arc-theme https://github.com/horst3180/arc-theme
Copyright 2015 horst3180 (https://github.com/horst3180)

feedagregator.svg and its .png derivatives come from
https://commons.wikimedia.org/wiki/File:Rss-feed.svg which is in the
public domain.

The other icons are modified versions of icons from the elementary project
Copyright 2007-2013 elementary LLC.


Constants and functions
"""
import pickle
import os
import warnings
import gettext
import logging
from logging.handlers import TimedRotatingFileHandler
from configparser import ConfigParser
from subprocess import check_output, CalledProcessError
from locale import getdefaultlocale
from glob import glob
from tkinter import colorchooser

import babel
from dateutil.tz import gettz
from bs4 import BeautifulSoup


APP_NAME = "FeedAgregator"


# --- paths
PATH = os.path.dirname(__file__)

if os.access(PATH, os.W_OK) and os.path.exists(os.path.join(PATH, "images")):
    # the app is not installed
    # local directory containing config files
    LOCAL_PATH = os.path.join(PATH, 'config')
    if not os.path.exists(LOCAL_PATH):
        os.mkdir(LOCAL_PATH)
    PATH_LOCALE = os.path.join(PATH, "locale")
    PATH_IMAGES = os.path.join(PATH, "images")
else:
    # local directory containing config files
    LOCAL_PATH = os.path.join(os.path.expanduser("~"), ".feedagregator")
    if not os.path.exists(LOCAL_PATH):
        os.mkdir(LOCAL_PATH)
    PATH_LOCALE = "/usr/share/locale"
    PATH_IMAGES = "/usr/share/feedagregator/images"

PATH_DATA = os.path.join(LOCAL_PATH, "data")
if not os.path.exists(PATH_DATA):
    os.mkdir(PATH_DATA)
PATH_FEEDS = os.path.join(LOCAL_PATH, "feeds.conf")
PATH_LATESTS = os.path.join(LOCAL_PATH, "latests.conf")
PATH_CONFIG = os.path.join(LOCAL_PATH, "feedagregator.ini")
PIDFILE = os.path.join(LOCAL_PATH, "feedagregator.pid")
PATH_LOG = os.path.join(LOCAL_PATH, "feedagregator.log")


# --- log
handler = TimedRotatingFileHandler(PATH_LOG, when='midnight',
                                   interval=1, backupCount=7)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(levelname)s: %(message)s',
                    handlers=[handler])
logging.getLogger().addHandler(logging.StreamHandler())


# --- config file
CONFIG = ConfigParser()
if os.path.exists(PATH_CONFIG):
    CONFIG.read(PATH_CONFIG)
else:
    CONFIG.add_section("General")
    CONFIG.set("General", "trayicon", "")
    CONFIG.set("General", "update_delay", "3600000")
    CONFIG.set("General", "img_timeout", "10")
    CONFIG.set("General", "language", getdefaultlocale()[0])
    CONFIG.set("General", "check_update", "True")
    CONFIG.set("General", "confirm_cat_remove", "True")
    CONFIG.set("General", "confirm_feed_remove", "True")
    CONFIG.set("General", "categories", "")
    CONFIG.set("General", "splash_supported", str(os.environ.get('DESKTOP_SESSION') != 'plasma'))
    CONFIG.set("General", "notifications", "True")
    CONFIG.add_section("Widget")
    CONFIG.set("Widget", "alpha", "80")
    CONFIG.set("Widget", 'font', 'Liberation\ Sans 10')
    CONFIG.set("Widget", 'font_title', 'Liberation\ Sans 12 bold')
    CONFIG.set("Widget", 'foreground', 'white')
    CONFIG.set("Widget", 'background', 'gray10')
    CONFIG.set("Widget", 'feed_foreground', 'white')
    CONFIG.set("Widget", 'feed_background', 'gray20')
    CONFIG.set("Widget", 'link_color', '#89B9F6')


def save_config():
    """Save configuration to file."""
    with open(PATH_CONFIG, 'w') as fichier:
        CONFIG.write(fichier)


# --- Translation
def available_langs():
    """Return list of available translations."""
    files = glob(os.path.join(PATH_LOCALE, '*', 'LC_MESSAGES', '%s.mo' % APP_NAME))
    langs = [file.split(os.path.sep)[-3] for file in files]
    return langs


# languages with an available translation {lang_id: full name}
LANGUAGES = {lang: babel.Locale.parse(lang).display_name for lang in available_langs()}
REV_LANGUAGES = {full_name: lang for lang, full_name in LANGUAGES.items()}

if not CONFIG.get("General", "language") in LANGUAGES:
    CONFIG.set("General", "language", "en_US")


gettext.bindtextdomain(APP_NAME, PATH_LOCALE)
gettext.textdomain(APP_NAME)

gettext.translation(APP_NAME, PATH_LOCALE,
                    languages=[CONFIG.get("General", "language")],
                    fallback=True).install()

# --- Time zone info
TZINFOS = {"AST": gettz('Atlantic Standard Time')}

# --- feed file
FEEDS = ConfigParser()
if os.path.exists(PATH_FEEDS):
    FEEDS.read(PATH_FEEDS)


def save_feeds():
    """Save feeds to file."""
    with open(PATH_FEEDS, 'w') as fichier:
        FEEDS.write(fichier)


LATESTS = ConfigParser()
if os.path.exists(PATH_LATESTS):
    LATESTS.read(PATH_LATESTS)
else:
    LATESTS.add_section('All')
    LATESTS.set("All", "geometry", "")
    LATESTS.set("All", 'position', 'normal')
    LATESTS.set("All", 'visible', 'True')


def save_latests():
    """Save feeds to file."""
    with open(PATH_LATESTS, 'w') as fichier:
        LATESTS.write(fichier)


def new_data_file():
    """Return unused name for feed data file."""
    l = os.listdir(PATH_DATA)
    i = 0
    name = "feed{}.dat"
    while name.format(i) in l:
        i += 1
    return name.format(i)


def save_data(filename, latest, data):
    """Save (pickle) feed data to filename."""
    with open(os.path.join(PATH_DATA, filename), 'wb') as file:
        pick = pickle.Pickler(file)
        pick.dump(latest)
        pick.dump(data)


def load_data(filename):
    """Load feed data from filename."""
    with open(os.path.join(PATH_DATA, filename), 'rb') as file:
        pick = pickle.Unpickler(file)
        latest = pick.load()
        data = pick.load()
    return latest, data


def feed_get_latest(filename):
    with open(os.path.join(PATH_DATA, filename), 'rb') as file:
        pick = pickle.Unpickler(file)
        latest = pick.load()
    return latest


# --- images
IM_ICON = os.path.join(PATH_IMAGES, "feedagregator.png")
IM_ICON_DISABLED = os.path.join(PATH_IMAGES, "feedagregator_dis.png")
IM_ICON_SVG = os.path.join(PATH_IMAGES, "feedagregator.svg")
IM_ICON_24 = os.path.join(PATH_IMAGES, "feedagregator24.png")
IM_ICON_48 = os.path.join(PATH_IMAGES, "feedagregator48.png")
IM_ICON_48_DISABLED = os.path.join(PATH_IMAGES, "feedagregator48_dis.png")
IM_MOINS_CLICKED = os.path.join(PATH_IMAGES, 'moins_clicked.png')
IM_MOINS_SEL = os.path.join(PATH_IMAGES, 'moins_sel.png')
IM_MOINS = os.path.join(PATH_IMAGES, 'moins.png')
IM_PLUS = os.path.join(PATH_IMAGES, 'plus.png')
IM_COLOR = os.path.join(PATH_IMAGES, 'color.png')
IM_IMG_MISSING = os.path.join(PATH_IMAGES, 'image_missing.png')
IM_HIDE_ALPHA = os.path.join(PATH_IMAGES, 'hide_alpha.png')
IM_OPENED_ALPHA = os.path.join(PATH_IMAGES, 'open_alpha.png')
IM_CLOSED_ALPHA = os.path.join(PATH_IMAGES, 'close_alpha.png')

ICONS = {key: os.path.join(PATH_IMAGES, '{}.png'.format(key))
         for key in ["information", "error", "question", "warning"]}
IM_SCROLL_ALPHA = os.path.join(PATH_IMAGES, "scroll.png")


# --- system tray icon
def get_available_gui_toolkits():
    """Check which GUI toolkits are available to create a system tray icon."""
    toolkits = {'gtk': True, 'qt': True, 'tk': True}
    b = False
    try:
        import gi
        b = True
    except ImportError:
        toolkits['gtk'] = False

    try:
        import PyQt5
        b = True
    except ImportError:
        try:
            import PyQt4
            b = True
        except ImportError:
            try:
                import PySide
                b = True
            except ImportError:
                toolkits['qt'] = False

    tcl_packages = check_output(["tclsh",
                                 os.path.join(PATH, "packages.tcl")]).decode().strip().split()
    toolkits['tk'] = "tktray" in tcl_packages
    b = b or toolkits['tk']
    if not b:
        raise ImportError("No GUI toolkits available to create the system tray icon.")
    return toolkits


TOOLKITS = get_available_gui_toolkits()
GUI = CONFIG.get("General", "trayicon").lower()

if not TOOLKITS.get(GUI):
    DESKTOP = os.environ.get('XDG_CURRENT_DESKTOP')
    if DESKTOP == 'KDE':
        if TOOLKITS['qt']:
            GUI = 'qt'
        else:
            warnings.warn("No version of PyQt was found, falling back to another GUI toolkits so the system tray icon might not behave properly in KDE.")
            GUI = 'gtk' if TOOLKITS['gtk'] else 'tk'
    else:
        if TOOLKITS['gtk']:
            GUI = 'gtk'
        elif TOOLKITS['qt']:
            GUI = 'qt'
        else:
            GUI = 'tk'
    CONFIG.set("General", "trayicon", GUI)

if GUI == 'tk':
    ICON = IM_ICON
    ICON_DISABLED = IM_ICON_DISABLED
else:
    ICON = IM_ICON_48
    ICON_DISABLED = IM_ICON_48_DISABLED


# --- colors
def is_color_light(color):
    r, g, b = color
    p = ((0.299 * r ** 2 + 0.587 * g ** 2 + 0.114 * b ** 2) ** 0.5) / 255
    return p > 0.5


def active_color(color, output='HTML'):
    """Return a lighter shade of color (RGB triplet with value max 255) in HTML format."""
    r, g, b = color
    if is_color_light(color):
        r *= 3 / 4
        g *= 3 / 4
        b *= 3 / 4
    else:
        r += (255 - r) / 3
        g += (255 - g) / 3
        b += (255 - b) / 3
    if output == 'HTML':
        return ("#%2.2x%2.2x%2.2x" % (round(r), round(g), round(b))).upper()
    else:
        return (round(r), round(g), round(b))


ZENITY = False

try:
    import tkcolorpicker as tkcp
except ImportError:
    tkcp = False

paths = os.environ['PATH'].split(":")
for path in paths:
    if os.path.exists(os.path.join(path, "zenity")):
        ZENITY = True


def askcolor(color=None, **options):
    """ plateform specific color chooser
        return the chose color in #rrggbb format """
    if tkcp:
        color = tkcp.askcolor(color, **options)
        if color:
            return color[1]
        else:
            return None
    elif ZENITY:
        try:
            args = ["zenity", "--color-selection", "--show-palette"]
            if "title" in options:
                args += ["--title", options["title"]]
            if color:
                args += ["--color", color]
            color = check_output(args).decode("utf-8").strip()
            if color:
                if color[0] == "#":
                    if len(color) == 13:
                        color = "#%s%s%s" % (color[1:3], color[5:7], color[9:11])
                elif color[:4] == "rgba":
                    color = color[5:-1].split(",")
                    color = '#%02x%02x%02x' % (int(color[0]), int(color[1]), int(color[2]))
                elif color[:3] == "rgb":
                    color = color[4:-1].split(",")
                    color = '#%02x%02x%02x' % (int(color[0]), int(color[1]), int(color[2]))
                else:
                    raise TypeError("Color formatting not understood.")
            return color
        except CalledProcessError:
            return None
        except Exception:
            color = colorchooser.askcolor(color, **options)
            return color[1]
    else:
        color = colorchooser.askcolor(color, **options)
        return color[1]


# --- compatibility
def add_trace(variable, mode, callback):
    """
    Add trace to variable.

    Ensure compatibility with old and new trace method.
    mode: "read", "write", "unset" (new syntax)
    """
    try:
        return variable.trace_add(mode, callback)
    except AttributeError:
        # fallback to old method
        return variable.trace(mode[0], callback)


def remove_trace(variable, mode, cbname):
    """
    Remove trace from variable.

    Ensure compatibility with old and new trace method.
    mode: "read", "write", "unset" (new syntax)
    """
    try:
        variable.trace_remove(mode, cbname)
    except AttributeError:
        # fallback to old method
        variable.trace_vdelete(mode[0], cbname)


def info_trace(variable):
    """
    Remove trace from variable.

    Ensure compatibility with old and new trace method.
    mode: "read", "write", "unset" (new syntax)
    """
    try:
        return variable.trace_info()
    except AttributeError:
        return variable.trace_vinfo()


# --- misc
def html2text(html):
    """Convert html string to basic text string."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text()


def internet_on():
    """Check the Internet connexion."""
    try:
        check_output(["ping", "-c", "1", "www.google.com"])
        return True
    except CalledProcessError:
        return False
