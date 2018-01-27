FeedAgregator
=============
RSS and Atom feed agregator in desktop widgets + notifications
--------------------------------------------------------------
Copyright 2018 Juliette Monsel <j_4321@protonmail.com>

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

    FeedAgregator is available on `AUR <https://aur.archlinux.org/packages/feedagregator>`__.

- Ubuntu

    FeedAgregator is available in the PPA `ppa:j-4321-i/ppa`.

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
     - feedparser https://pypi.python.org/pypi/feedparser
     - Pillow https://pypi.python.org/pypi/Pillow

    You also need to have at least one of the following GUI toolkits for the system tray icon:
     - Tktray https://code.google.com/archive/p/tktray/downloads
     - PyGTK http://www.pygtk.org/downloads.html
     - PyQt5, PyQt4 or PySide

    If you are using a Tcl/Tk version < 8.6, you will also need PIL.


    For instance, in Ubuntu/Debian you will need to install the following packages:
    python3-tk, tk-tktray, libnotify-bin and the notification server of your choice,
    tk-html3, python3-bs4, python3-babel, python3-feedparser,
    python3-pil and python3-pil.imagek

    In Archlinux, you will need to install the following packages:
    tk, tktray (`AUR <https://aur.archlinux.org/packages/tktray>`__),
    libnotify and the notification server of your choice,
    python-beautifulsoup4, python-babel, python-feedparser, python-pillow,
    tkhtml3-git (`AUR <https://aur.archlinux.org/packages/tkhtml3-git>`__)

    Then install the application:
    ::
        $ sudo python3 setup.py install

    You can now launch it from `Menu > Network > FeedAgregator`. You can launch
    it from the command line with `feedagregator`.


Troubleshooting
---------------

Several gui toolkits are available to display the system tray icon, so if the
icon does not behave properly, try to change toolkit, they are not all fully
compatible with every desktop environment.

If there is a problem with the font of the number of unread mails, try to change
the font from the settings.

If you encounter bugs or if you have suggestions, please open an issue on
`GitHub <https://github.com/j4321/FeedAgregator/issues>`__ or write me an email
at <j_4321@protonmail.com>.

