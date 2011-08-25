#! /usr/bin/env python
import urllib2
import urlparse
import csv
import sys
from BeautifulSoup import BeautifulSoup
import re


encoding_re = re.compile("charset\s*=\s*(\S+?)(;|$)")
html_re = re.compile(": text/html")
def encoding_from_content_type(content_type):
    """
    Extracts the charset from a Content-Type header.

    >>> encoding_from_content_type('text/html; charset=utf-8')
    'utf-8'
    >>> encoding_from_content_type('text/html')
    >>>
    """

    if not content_type:
        return None
    match = encoding_re.search(content_type)
    return match and match.group(1) or None

class NotHtmlException(Exception):
    pass

def get_url(url, referer=''):
    req = urllib2.Request(url, None, {'User-Agent': 'Fusionbox spider', 'Referer': referer})
    response = urllib2.urlopen(req)
    content_type = response.info().getfirstmatchingheader('content-type')
    if content_type:
        if not html_re.search(content_type[0]):
            raise NotHtmlException
        encoding = encoding_from_content_type(content_type[0])
    else:
        encoding = None
    try:
        return BeautifulSoup(response.read(), fromEncoding=encoding)
    except UnicodeEncodeError:
        raise NotHtmlException


def scrape_url(url, referer=''):
    html = get_url(url, referer)

    links = [urlparse.urljoin(url, i['href'], False) for i in html.findAll('a', href=True)]

    title = html.head.title.contents
    description = html.head.findAll('meta', {"name":"description"})
    keywords = html.head.findAll('meta', {"name":"keywords"})
    if title:
        title = title[0]
    else:
        title = ''
    if description:
        description = description[0]['content']
    else:
        description = ''
    if keywords:
        keywords = keywords[0]['content']
    else:
        keywords = ''
    return (links, title, description, keywords)


def spider(base):
    visited = set()
    to_visit = set([(base, base)])

    base_domain = urlparse.urlparse(base).netloc
    writer = csv.writer(sys.stdout)
    while to_visit:
        (url, referer) = to_visit.pop()
        if  url in visited:
            continue
        visited.add(url)
        try:
            data = (links, title, description, keywords) = scrape_url(url, referer)
        except urllib2.URLError as e:
            sys.stderr.write('Error: %s: %s. Referred by %s\n' % (url, e, referer))
            continue
        except NotHtmlException:
            continue
        for link in links:
            parsed = urlparse.urlparse(link)
            if parsed.netloc == base_domain:
                to_visit.add((link, url))
        writer.writerow(data)


if __name__ == '__main__':
    spider(sys.argv[1])
