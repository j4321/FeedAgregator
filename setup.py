#! /usr/bin/python3
# -*- coding:Utf-8 -*-

import os

from setuptools import setup

images = [os.path.join("feedagregatorlib/images/", img) for img in os.listdir("feedagregatorlib/images/")]
data_files = [("/usr/share/applications", ["feedagregator.desktop"]),
              ("/usr/share/feedagregator/images/", images),
              ("/usr/share/doc/feedagregator/", ["README.rst", "changelog"]),
              ("/usr/share/man/man1", ["feedagregator.1.gz"]),
              ("/usr/share/locale/en_US/LC_MESSAGES/", ["feedagregatorlib/locale/en_US/LC_MESSAGES/FeedAgregator.mo"]),
              ("/usr/share/locale/fr_FR/LC_MESSAGES/", ["feedagregatorlib/locale/fr_FR/LC_MESSAGES/FeedAgregator.mo"]),
              ("/usr/share/pixmaps", ["feedagregator.svg"])]

with open("feedagregatorlib/version.py") as file:
    exec(file.read())

setup(name="feedagregator",
      version=__version__,
      description="RSS and Atom feed agregator in desktop widgets + notifications",
      author="Juliette Monsel",
      author_email="j_4321@protonmail.com",
      license="GPLv3",
      url="https://github.com/j4321/FeedAgregator/",
      packages=['feedagregatorlib',
                'feedagregatorlib.settings',
                'feedagregatorlib.trayicon',
                'feedagregatorlib.widgets'],
      package_data={'feedagregatorlib': ["packages.tcl"]},
      scripts=["feedagregator"],
      data_files=data_files,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: X11 Applications',
          'Intended Audience :: End Users/Desktop',
          'Topic :: Office/Business',
          'Topic :: Internet',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Natural Language :: English',
          'Natural Language :: French',
          'Operating System :: POSIX :: Linux',
      ],
      long_description="""
FeedAgregator periodically looks for RSS/Atom feed updates.
If an update is found, a notification is sent. In addition, a desktop
widget show the latest entry of all feeds and for each feed, a widget
shows all entries.
""",
      install_requires=["babel", "beautifulsoup4", "feedparser", 'pillow',
                        'python-dateutil', 'ewmh'])
