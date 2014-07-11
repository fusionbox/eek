#!/usr/bin/env python
import os
import re
from setuptools import setup

__doc__="""
Eek is an HTTP spider that collects metadata from HTML
"""

install_requires = ['requests>=1.0.0']
try:
    import argparse
except:
    install_requires.append('argparse')

version = '0.0.1'

setup(name='Eek',
    version=version,
    description='eek',
    author='Gavin Wahl',
    author_email='gwahl@fusionbox.com',
    long_description=__doc__,
    packages=['eek'],
    scripts=['eek/eek'],
    platforms = "any",
    license='BSD',
    test_suite='tests',
    install_requires=install_requires,
)
