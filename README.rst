Eek
===

Eek is a web crawler that outputs metadata about a website in CSV
format.

Installation
------------

::

    $ pip install eek

Usage
-----

usage: eek [-h] [--graph] [--delay SECONDS] [--grep PATTERN] [-i] URL

eek recursively crawls a website, outputing metadata about each page in
CSV format.

::

    positional arguments:
      URL                The base URL to start the crawl

    optional arguments:
      -h, --help         show this help message and exit
      --graph            output a graphviz digraph of links instead of CSV
                         metadata
      --delay SECONDS    Time, in seconds, to wait in between fetches. Defaults to
                         0.
      --grep PATTERN     Print urls containing PATTERN (a python regular
                         expression).
      -i, --ignore-case  Ignore case. Only valid with --grep

Example:

::

    eek http://example.com/

To save output to a file, use redirection

::

    eek http://example.com/ > ~/some_file.csv

To slow down crawling, use ``--delay=[seconds]``
