#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
FeedAgregator - RSS and Atom feed agregator in desktop widgets + notifications
Copyright 2018-2019 Juliette Monsel <j_4321@protonmail.com>
code based on the tkinterhtml module by Aivar Annamaa copyright 2015-2016
https://pypi.python.org/pypi/tkinterhtml

FeedAgregator is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

FeedAgregator is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PaURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


Wrapper for the Tkhtml widget from http://tkhtml.tcl.tk/tkhtml.html
"""


import traceback
import warnings
import logging
import tkinter as tk
from tkinter import ttk
from urllib.request import urlopen
from webbrowser import open as webOpen

from PIL.ImageTk import PhotoImage

from .constants import IM_IMG_MISSING, CONFIG


_tkhtml_loaded = False


def load_tkhtml(master, location=None):
    global _tkhtml_loaded
    if not _tkhtml_loaded:
        if location:
            master.tk.eval('global auto_path; lappend auto_path {%s}' % location)
        master.tk.eval('package require Tkhtml')
        _tkhtml_loaded = True


class TkinterHtml(tk.Widget):
    def __init__(self, master, cfg={}, **kw):
        """
        See options descriptions from here: http://tkhtml.tcl.tk/tkhtml.html
        """
        load_tkhtml(master)

        if "imagecmd" not in kw:
            kw["imagecmd"] = master.register(self._fetch_image)

        tk.Widget.__init__(self, master, 'html', cfg, kw)

        # make selection and copying possible
        self._selection_start_node = None
        self._selection_start_offset = None
        self._selection_end_node = None
        self._selection_end_offset = None
        self.bind("<1>", self._on_click, True)
        self.bind("<B1-Motion>", self._extend_selection, True)
        self.bind("<Motion>", self._on_motion)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Leave>", self._on_focus_out)
        self.bind("<<Copy>>", self.copy_selection_to_clipboard, True)
        self.bind("<Control-c>", self._ctrl_c, True)
        self.bind_class('Html', '<Button-5>', lambda e: None)
        self.bind('Html', '<Button-4>', lambda e: None)

        self._image_name_prefix = str(id(self)) + "_img_"
        self._images = set()  # to avoid garbage collecting images
        # self._images.add(PhotoImage(data=IMG_MISSING, name=self._image_name_prefix + 'missing'))
        self._images.add(PhotoImage(file=IM_IMG_MISSING, name=self._image_name_prefix + 'missing'))

        self._last_node = None

        self.tk.call(self._w, "handler", "script", "script", self.register(self._on_script))
        self.tk.call(self._w, "handler", "script", "style", self.register(self._on_style))

    @staticmethod
    def keys():
        keys = ['fontscale', 'fonttable', 'forcefontmetrics', 'forcewidth',
                'defaultstyle', 'imagecache', 'imagecmd', 'mode', 'shrink',
                'parsemode', 'zoom']
        return keys

    def bbox(self, node_handle=None):
        if node_handle is None:
            return self.tk.call(self._w, "bbox", self.node())
        else:
            return self.tk.call(self._w, "bbox", node_handle)

    def node(self, *arguments):
        return self.tk.call(self._w, "node", *arguments)

    def parse(self, *args):
        source = args[0]
        if "<title>" in source.lower():
            warnings.warn("64-bit Windows Tkhtml has problems with html source containing <title> element. Consider removing it before sending source to parse.\n")
        self.tk.call(self._w, "parse", *args)

    def reset(self):
        return self.tk.call(self._w, "reset")

    def tag(self, subcommand, tag_name, *arguments):
        return self.tk.call(self._w, "tag", subcommand, tag_name, *arguments)

    def text(self, *args):
        return self.tk.call(self._w, "text", *args)

    def xview(self, *args):
        "Used to control horizontal scrolling."
        if args:
            return self.tk.call(self._w, "xview", *args)
        coords = map(float, self.tk.call(self._w, "xview").split())
        return tuple(coords)

    def xview_moveto(self, fraction):
        """Adjusts horizontal position of the widget so that fraction
        of the horizontal span of the document is off-screen to the left.
        """
        return self.xview("moveto", fraction)

    def xview_scroll(self, number, what):
        """Shifts the view in the window according to number and what;
        number is an integer, and what is either 'units' or 'pages'.
        """
        return self.xview("scroll", number, what)

    def yview(self, *args):
        "Used to control the vertical position of the document."
        if args:
            return self.tk.call(self._w, "yview", *args)
        coords = map(float, self.tk.call(self._w, "yview").split())
        return tuple(coords)

    def yview_name(self, name):
        """Adjust the vertical position of the document so that the tag
        <a name=NAME...> is visible and preferably near the top of the window.
        """
        return self.yview(name)

    def yview_moveto(self, fraction):
        """Adjust the vertical position of the document so that fraction of
        the document is off-screen above the visible region.
        """
        return self.yview("moveto", fraction)

    def yview_scroll(self, number, what):
        """Shifts the view in the window up or down, according to number and
        what. 'number' is an integer, and 'what' is either 'units' or 'pages'.
        """
        return self.yview("scroll", number, what)

    def _on_script(self, *args):
        "Currently just ignoring script"

    def _on_style(self, *args):
        "Currently just ignoring style"
        return self.tk.call(self._w, "style", *args)

    def style(self, *args):
        "set style"
        return self.tk.call(self._w, "style", *args)

    def _fetch_image(self, *args):
        assert len(args) == 1
        url = args[0]
        name = self._image_name_prefix + str(len(self._images))
        try:
            with urlopen(url, timeout=CONFIG.getint("General", "img_timeout", fallback=10)) as handle:
                data = handle.read()
        except Exception as e:
            logging.error('Error: %s\nurl=%s', str(e), url)
            name = self._image_name_prefix + 'missing'
        else:
            try:
                self._images.add(PhotoImage(name=name, data=data))
            except Exception as e:
                logging.error('Error in tkinterhtml: %s\nurl=%s', str(e), url)
                name = self._image_name_prefix + 'missing'
        return name

    def _get_node_text(self, node_handle):
        return self.tk.call(node_handle, "text")

    def _get_node_tag(self, node_handle):
        return self.tk.call(node_handle, "tag")

    def _get_node_parent(self, node_handle):
        return self.tk.call(node_handle, "parent")

    def _get_node_attribute(self, node_handle, attribute):
        return self.tk.call(node_handle, "attribute", attribute)

    def _set_node_dynamic(self, node_handle, flag):
        return self.tk.call(node_handle, "dynamic", "set", flag)

    def _clear_node_dynamic(self, node_handle, flag):
        return self.tk.call(node_handle, "dynamic", "clear", flag)

    def _on_click(self, event):
        self._start_selection(event)
        try:
            node_handle, offset = self.node(True, event.x, event.y)
            # open link in web browser
            if self._get_node_tag(node_handle) == "a":
                webOpen(self._get_node_attribute(node_handle, "href"))
            elif self._get_node_tag(self._get_node_parent(node_handle)) == "a":
                webOpen(self._get_node_attribute(self._get_node_parent(node_handle), "href"))
        except ValueError:
            # self.node returned None
            pass

    def _on_focus_out(self, event):
        self._last_node = None

    def _on_motion(self, event):
        """ set 'hover' tag to the node over which the cursor is. """
        try:
            if self._last_node:
                self._clear_node_dynamic(self._last_node, "hover")
            node_handle, offset = self.node(True, event.x, event.y)
            self._last_node = self._get_node_parent(node_handle)
            self._set_node_dynamic(self._last_node, "hover")
        except ValueError:
            pass

    def _start_selection(self, event):
        self.focus_force()
        self.tag("delete", "selection")
        try:
            self._selection_start_node, self._selection_start_offset = self.node(True, event.x, event.y)
        except ValueError:
            self._selection_start_node = None
        except Exception:
            self._selection_start_node = None
            traceback.print_exc()

    def _extend_selection(self, event):
        if self._selection_start_node is None:
            return

        try:
            self._selection_end_node, self._selection_end_offset = self.node(True, event.x, event.y)
        except ValueError:
            self._selection_end_node = None
        except Exception:
            self._selection_end_node = None
            traceback.print_exc()

        try:
            self.tag("add", "selection",
                     self._selection_start_node, self._selection_start_offset,
                     self._selection_end_node, self._selection_end_offset)
        except tk.TclError:
            pass

    def _ctrl_c(self, event):
        if self.focus_get() == self:
            self.copy_selection_to_clipboard()

    def copy_selection_to_clipboard(self, event=None):
        if self._selection_start_node is None or self._selection_end_node is None:
            return

        start_index = self.text("offset", self._selection_start_node, self._selection_start_offset)
        end_index = self.text("offset", self._selection_end_node, self._selection_end_offset)
        if start_index > end_index:
            start_index, end_index = end_index, start_index
        whole_text = self.text("text")
        selected_text = whole_text[start_index:end_index]
        self.clipboard_clear()
        self.clipboard_append(selected_text)


class HtmlFrame(ttk.Frame):
    def __init__(self, master, **kw):
        """All keyword arguments not listed here are sent to contained TkinterHtml.
        See descriptions of the options here: http://tkhtml.tcl.tk/tkhtml.html
        """
        keys = list(kw.keys())
        html_kw = {key: kw.pop(key) for key in keys if key in TkinterHtml.keys()}
        ttk.Frame.__init__(self, master, **kw)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.grid_propagate(False)

        html = self.html = TkinterHtml(self, **html_kw)
        html.grid(row=0, column=0, sticky="nswe")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.set_content("<html><body></body></html>")

    def set_content(self, html_source):
        self.html.reset()
        if "</body>" not in html_source:
            content = "<html><body>{}</body></html>".format(html_source)
        else:
            content = html_source
        self.html.parse(content)

    def set_style(self, stylesheet):
        """ stylesheet: string containing css style configuration """
        self.html.style(stylesheet)

    def set_font_size(self, size):
        """Set medium font size to size and change the rest of the font table accordingly."""
        fonttable = list(self.html.cget('fonttable'))
        delta = size - fonttable[3]
        fonttable = [s + delta for s in fonttable]
        self.html.configure(fonttable=fonttable)
