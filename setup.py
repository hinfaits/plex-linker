#!/usr/bin/env python

from setuptools import setup

setup(name='plex-linker',
      version='0.0.1',
      description='Generate symlinks in a Plex compatible directory structure for TV shows',
      author='Aaron Tsui',
      author_email='hinfaits@users.noreply.github.com',
      url='https://github.com/hinfaits/plex-linker',
      packages=['plex_linker',],
      entry_points={'console_scripts': ['plex-linker=plex_linker.app:main'],},
     )
