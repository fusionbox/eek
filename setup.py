#!/usr/bin/env python
import os
import re
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

install_requires = [
    'requests>=1.0.0',
    'beautifulsoup4',
]

try:
    import argparse
except:
    install_requires.append('argparse')

version = '1.0.2'

setup(
    name='eek',
    version=version,
    description='Eek, a [web] spider.',
    author='Gavin Wahl',
    author_email='gwahl@fusionbox.com',
    long_description=read('README.rst'),
    url='https://github.com/fusionbox/eek',
    packages=['eek'],
    scripts=['eek/eek'],
    platforms = "any",
    license='BSD',
    test_suite='tests',
    install_requires=install_requires,
)
