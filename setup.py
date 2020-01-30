#!/usr/bin/env python
from distutils.core import setup

setup(name='mensa-aachen',
      version='1.0',
      description='Neat library for fetching and parsing the menu of Studierendenwerk Aachen\'s canteens',
      author='Michael Thies',
      author_email='mail@mhthies.de',
      url='https://gitea.nephos.link/michael/mensa_aachen',
      py_modules=['mensa_aachen'],
      python_requires='>=3.6',
      install_requires=[
          'requests>=2.22',
          'beautifulsoup4>=4.8',
          'lxml>=4.4, <5',
      ],
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
          "Development Status :: 4 - Beta",
      ],
      )
