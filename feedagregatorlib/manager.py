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


Feed manager dialog
"""
from tkinter import Toplevel
from tkinter.ttk import Entry, Button, Treeview

from PIL.ImageTk import PhotoImage

from feedagregatorlib.constants import FEEDS, IM_MOINS, IM_PLUS, \
    IM_MOINS_SEL, IM_MOINS_CLICKED, APP_NAME, LATESTS, CONFIG
from feedagregatorlib.add import Add
from feedagregatorlib.messagebox import askokcancel
from feedagregatorlib.autoscrollbar import AutoScrollbar
from feedagregatorlib.autocomplete import AutoCompleteCombobox


class Manager(Toplevel):
    def __init__(self, master):
        Toplevel.__init__(self, master, class_=APP_NAME)
        self.title(_("Manage Feeds"))
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.im_moins = PhotoImage(master=self, file=IM_MOINS)
        self.im_moins_sel = PhotoImage(master=self, file=IM_MOINS_SEL)
        self.im_moins_clicked = PhotoImage(master=self, file=IM_MOINS_CLICKED)
        self.im_plus = PhotoImage(master=self, file=IM_PLUS)

        self._no_edit_entry = self.register(lambda: False)

        self.change_made = False

        self.categories = set(LATESTS.sections())
        self.categories.remove('All')
        self.categories.add('')

        # --- treeview
        self.tree = Treeview(self, columns=('Title', 'URL', 'Category', 'Remove'),
                             style='manager.Treeview',
                             selectmode='none')
        self.tree.heading('Title', text=_('Title'),
                          command=lambda: self._sort_column('Title', False))
        self.tree.heading('URL', text=_('URL'),
                          command=lambda: self._sort_column('URL', False))
        self.tree.heading('Category', text=_('Category'),
                          command=lambda: self._sort_column('Category', False))
        self.tree.column('#0', width=14, stretch=False)
        self.tree.column('Title', width=250)
        self.tree.column('URL', width=350)
        self.tree.column('Category', width=150)
        self.tree.column('Remove', width=20, minwidth=20, stretch=False)

        y_scroll = AutoScrollbar(self, orient='vertical',
                                 command=self.tree.yview)
        x_scroll = AutoScrollbar(self, orient='horizontal',
                                 command=self.tree.xview)
        self.tree.configure(xscrollcommand=x_scroll.set,
                            yscrollcommand=y_scroll.set)

        self.tree.bind('<Motion>', self._highlight_active)
        self.tree.bind('<Leave>', self._leave)
        self._last_active_item = None

        # --- populate treeview
        for title in sorted(FEEDS.sections(), key=lambda x: x.lower()):
            item = self.tree.insert('', 'end',
                                    values=(title, FEEDS.get(title, 'url'),
                                            FEEDS.get(title, 'category', fallback=''),
                                            ''))
            if FEEDS.getboolean(title, 'active', fallback=True):
                self.tree.selection_add(item)
            self.tree.item(item, tags=item)
            self.tree.tag_configure(item, image=self.im_moins)
            self.tree.tag_bind(item, '<ButtonRelease-1>',
                               lambda event, i=item: self._click_release(event, i))
            self.tree.tag_bind(item, '<ButtonPress-1>',
                               lambda event, i=item: self._press(event, i))
            self.tree.tag_bind(item, '<Double-1>',
                               lambda event, i=item: self._edit(event, i))

        self.tree.grid(row=0, column=0, sticky='ewsn')
        x_scroll.grid(row=1, column=0, sticky='ew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        Button(self, image=self.im_plus, command=self.feed_add,
               style='manager.TButton').grid(row=2, column=0, columnspan=2,
                                             sticky='e', padx=4, pady=4)
        self._check_add_id = ''

    def destroy(self):
        try:
            self.after_cancel(self._check_add_id)
        except ValueError:
            pass
        Toplevel.destroy(self)

    def _edit(self, event, item):
        """Edit feed title / category."""
        column = self.tree.identify_column(event.x)
        if column in ['#1', '#2']:
            bbox = self.tree.bbox(item, column)
            entry = Entry(self.tree)
            entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3],
                        anchor='nw')
            entry.bind('<Escape>', lambda e: entry.destroy())
            entry.bind('<FocusOut>', lambda e: entry.destroy())
            if column == '#1':
                entry.insert(0, self.tree.item(item, 'values')[0])
                entry.configure(style='manager.TEntry')

                def ok(event):
                    name = entry.get()
                    if name:
                        name = self.master.feed_rename(self.tree.set(item, 'Title'), name)
                        self.tree.set(item, 'Title', name)
                    entry.destroy()

                entry.bind('<Return>', ok)
            else:
                entry.insert(0, self.tree.item(item, 'values')[1])
                entry.configure(style='no_edit.TEntry', validate='key',
                                validatecommand=self._no_edit_entry)

            entry.selection_range(0, 'end')
            entry.focus_set()
        elif column == '#3':

            def focus_out(event):
                x, y = self.tree.winfo_pointerxy()
                x0 = combo.winfo_rootx()
                x1 = x0 + combo.winfo_width()
                y0 = combo.winfo_rooty()
                y1 = y0 + combo.winfo_height()
                if not (x0 <= x <= x1 and y0 <= y <= y1):
                    combo.destroy()

            def ok(event):
                category = combo.get().strip()
                self.categories.add(category)
                self.master.feed_change_cat(self.tree.set(item, 'Title'),
                                            self.tree.set(item, 'Category'),
                                            category)
                self.tree.set(item, 'Category', category)
                combo.destroy()

            bbox = self.tree.bbox(item, column)
            cat = list(self.categories)
            combo = AutoCompleteCombobox(self.tree, values=cat, allow_other_values=True)
            combo.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3],
                        anchor='nw')
            combo.bind('<Escape>', lambda e: combo.destroy())
            combo.bind('<FocusOut>', focus_out)
            combo.bind('<Return>', ok)
            combo.bind('<<ComboboxSelected>>', ok)
            combo.current(cat.index(self.tree.set(item, '#3')))

    def _press(self, event, item):
        if self.tree.identify_column(event.x) == '#4':
            self.tree.tag_configure(item, image=self.im_moins_clicked)

    def _click_release(self, event, item):
        """Handle click on items."""
        if self.tree.identify_row(event.y) == item:
            if self.tree.identify_column(event.x) == '#4':
                title = self.tree.item(item, 'values')[0]
                rep = True
                if CONFIG.getboolean('General', 'confirm_remove', fallback=True):
                    rep = askokcancel(_('Confirmation'),
                                      _('Do you want to remove the feed {feed}?').format(feed=title))
                if rep:
                    self.master.feed_remove(title)
                    self.tree.delete(item)
                    self.change_made = True
            elif self.tree.identify_element(event.x, event.y) == 'Checkbutton.indicator':
                sel = self.tree.selection()
                if item in sel:
                    self.tree.selection_remove(item)
                    self.master.feed_set_active(self.tree.set(item, '#1'), False)
                else:
                    self.tree.selection_add(item)
                    self.master.feed_set_active(self.tree.set(item, '#1'), True)
                self.change_made = True
        else:
            self.tree.tag_configure(item, image=self.im_moins)

    def _leave(self, event):
        """Remove highlight when mouse leave the treeview."""
        if self._last_active_item is not None:
            self.tree.tag_configure(self._last_active_item, image=self.im_moins)

    def _highlight_active(self, event):
        """Highlight minus icon under the mouse."""
        if self._last_active_item is not None:
            self.tree.tag_configure(self._last_active_item, image=self.im_moins)
        if self.tree.identify_column(event.x) == '#4':
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.tag_configure(item, image=self.im_moins_sel)
                self._last_active_item = item
            else:
                self._last_active_item = None
        else:
            self._last_active_item = None

    def _sort_column(self, column, reverse):
        """Sort column by (reversed) alphabetical order."""
        l = [(self.tree.set(c, column), c) for c in self.tree.get_children('')]
        l.sort(reverse=reverse, key=lambda x: x[0].lower())
        for index, (val, c) in enumerate(l):
            self.tree.move(c, "", index)
        self.tree.heading(column,
                          command=lambda: self._sort_column(column, not reverse))

    def feed_add(self):
        dialog = Add(self)
        self.wait_window(dialog)
        url = dialog.url
        if url:
            self.configure(cursor='watch')
            queue = self.master.feed_add(url, manager=True)
            self._check_add_id = self.after(1000, self._check_add_finished, url, queue)

    def _check_add_finished(self, url, queue):

        if queue.empty():
            self._check_add_id = self.after(1000, self._check_add_finished, url, queue)
        else:
            title = queue.get(False)
            if title:
                item = self.tree.insert('', 'end', values=(title, url, ''))
                self.tree.item(item, tags=item)
                self.tree.tag_configure(item, image=self.im_moins)
                self.tree.tag_bind(item, '<ButtonRelease-1>',
                                   lambda event: self._click_release(event, item))
                self.tree.tag_bind(item, '<ButtonPress-1>',
                                   lambda event: self._press(event, item))
                self.tree.tag_bind(item, '<Double-1>',
                                   lambda event: self._edit(event, item))
                self.tree.selection_add(item)

                self.change_made = True
            self.configure(cursor='arrow')
            self.focus_set()
            self.grab_set()
