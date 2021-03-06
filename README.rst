FeedAgregator
=============
RSS and Atom feed agregator in desktop widgets + notifications
--------------------------------------------------------------
Copyright 2018-2019 Juliette Monsel <j_4321@protonmail.com>

FeedAgregator periodically looks for RSS/Atom feed updates.
If an update is found, a notification is sent. In addition, desktop widgets
display either all the entries of one feed or the latest entry of each
feed of a given category.

FeedAgregator is designed for Linux. It is written in Python 3 and relies
mostly upon Tk GUI toolkit. The application is in the system tray, so it
might not work with all desktop environments (see Troubleshooting).


Install
-------

- Archlinux

    FeedAgregator is available in `AUR <https://aur.archlinux.org/packages/feedagregator>`__.

- Ubuntu

    FeedAgregator is available in the PPA `ppa:j-4321-i/ppa <https://launchpad.net/~j-4321-i/+archive/ubuntu/ppa>`__.

    ::

        $ sudo add-apt-repository ppa:j-4321-i/ppa
        $ sudo apt-get update
        $ sudo apt-get install feedagregator

- Source code

    First, install the missing dependencies among:

     - Tkinter (Python wrapper for Tk)
     - Tkhtml3 http://tkhtml.tcl.tk/
     - libnotify and a notification server if your desktop environment does not provide one.
       (see https://wiki.archlinux.org/index.php/Desktop_notifications for more details)
     - Beautifulsoup 4 https://pypi.python.org/pypi/beautifulsoup4/
     - babel https://pypi.python.org/pypi/Babel
     - dateutil https://pypi.python.org/pypi/python-dateutil
     - feedparser https://pypi.python.org/pypi/feedparser
     - ewmh https://pypi.python.org/pypi/ewmh
     - Pillow https://pypi.python.org/pypi/Pillow

    You also need to have at least one of the following GUI toolkits for the system tray icon:

     - Tktray https://code.google.com/archive/p/tktray/downloads
     - PyGTK http://www.pygtk.org/downloads.html
     - PyQt5, PyQt4 or PySide

    For instance, in Ubuntu/Debian you will need to install the following packages:
    python3-tk, tk-tktray, libnotify-bin and the notification server of your choice,
    tk-html3, python3-bs4, python3-babel, python3-feedparser, python3-dateutil,
    python3-ewmh, python3-pil and python3-pil.imagek

    In Archlinux, you will need to install the following packages:
    tk, tktray (`AUR <https://aur.archlinux.org/packages/tktray>`__),
    libnotify and the notification server of your choice, python-dateutil,
    python-beautifulsoup4, python-babel, python-feedparser, python-pillow,
    tkhtml3-git (`AUR <https://aur.archlinux.org/packages/tkhtml3-git>`__)
    python-ewmh (`AUR <https://aur.archlinux.org/packages/python-ewmh>`__)

    Then install the application:
    
    ::
    
        $ sudo python3 setup.py install

    You can now launch it from *Menu > Network > FeedAgregator*. You can launch
    it from the command line with `feedagregator`.

Feed management
---------------

Feeds can be managed by clicking on *Manage feeds* in the main menu 
(right click on the tray icon). A window containing the list of feeds 
opens:

- Tick / untick the box on the left to activate / deactivate a feed.
- Double click on the feed title to edit it.
- Double click on the category to edit it. The latest entry of each feed
  in the same category can be displayed in a widget.
- Click on the red minus sign on the right of a feed to delete it.
- Click on the green plus sign to add a feed.

Troubleshooting
---------------

Several GUI toolkits are available to display the system tray icon, so if the
icon does not behave properly, try to change toolkit, they are not all fully
compatible with every desktop environment.

If the widgets disappear when you click on them, open the setting dialog 
from the menu and check the box 'Check this box if the widgets disappear 
when you click'.

If you encounter bugs or if you have suggestions, please open an issue on
`GitHub <https://github.com/j4321/FeedAgregator/issues>`__ or write me an email
at <j_4321@protonmail.com>.

