#! /usr/bin/env python
import urllib2
import urlparse
import csv
import sys
from BeautifulSoup import BeautifulSoup
import re
import collections

import robotparser # this project's version

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
        bs = BeautifulSoup(response.read(), fromEncoding=encoding, convertEntities=BeautifulSoup.XML_ENTITIES)
        bs.base_url = response.geturl()
        return bs
    except UnicodeEncodeError:
        raise NotHtmlException


def scrape_html(html):
    links = [urlparse.urldefrag(urlparse.urljoin(html.base_url, i['href'], False))[0] for i in html.findAll('a', href=True)]

    try:
        title = html.head.title.contents[0]
    except (AttributeError, IndexError):
        title = ''
    try:
        description = html.head.findAll('meta', {"name":"description"})[0]['content']
    except (AttributeError, IndexError):
        description = ''
    try:
        keywords = html.head.findAll('meta', {"name":"keywords"})[0]['content']
    except (AttributeError, IndexError):
        keywords = ''

    return (links, title, description, keywords)


class UrlTask(tuple):
    """
    We need to keep track of referers, but we don't want to add a url multiple
    times just because it was referenced on multiple pages
    """
    def __hash__(self):
        return hash(self[0])
    def __eq__(self, other):
        return self[0] == other[0]

class VisitOnlyOnceClerk(object):
    def __init__(self):
        self.visited = set()
        self.to_visit = set()
    def enqueue(self, url, referer):
        if not url in self.visited:
            self.to_visit.add(UrlTask((url, referer)))
    def __bool__(self):
        return bool(self.to_visit)
    def __iter__(self):
        while self.to_visit:
            (url, referer) = self.to_visit.pop()
            self.visited.add(url)
            yield (url, referer)


def lremove(string, prefix):
    """
    Remove a prefix from a string, if it exists.
    >>> lremove('www.foo.com', 'www.')
    'foo.com'
    >>> lremove('foo.com', 'www.')
    'foo.com'
    """
    if string.startswith(prefix):
        return string[len(prefix):]
    else:
        return string

def spider(base, callback, clerk):
    clerk.enqueue(base, base)

    base_domain = lremove(urlparse.urlparse(base).netloc, 'www.')
    for (url, referer) in clerk:
        try:
            html = get_url(url, referer)
            data = (links, title, description, keywords) = scrape_html(html)
        except urllib2.URLError as e:
            sys.stderr.write('Error: %s: %s. Referred by %s\n' % (url, e, referer))
            continue
        except NotHtmlException:
            continue
        for link in links:
            parsed = urlparse.urlparse(link)
            if lremove(parsed.netloc, 'www.') == base_domain:
                clerk.enqueue(link, url)
        callback(url, data, html)


def metadata_spider(base, output = sys.stdout):
    writer = csv.writer(output)
    robots = robotparser.RobotFileParser(base + '/robots.txt')
    robots.read()
    writer.writerow(['url', 'title', 'description', 'keywords', 'allow', 'disallow', 'noindex', 'meta robots'])

    def callback(url, data, html):
        rules = applicable_robot_rules(robots, url)
        robots_meta = ','.join(i['content'] for i in html.findAll('meta', {"name":"robots"}))
        writer.writerow([i.encode('utf-8') for i in (url, data[1], data[2], data[3], ','.join(rules['allow']), ','.join(rules['disallow']), ','.join(rules['noindex']), robots_meta)])

    spider(base, callback, VisitOnlyOnceClerk())


def graphviz_spider(base):
    def callback(url, data):
        for link in data[0]:
            print '  "%s" -> "%s";' % (url, link)
    print "digraph links {"
    spider(base, callback, VisitOnlyOnceClerk())
    print "}"

def applicable_robot_rules(robots, url):
    rules = collections.defaultdict(list)
    if robots.default_entry:
        rules[robots.default_entry.allowance(url)].append('*')
    for entry in robots.entries:
        rules[entry.allowance(url)].extend(entry.useragents)
    return rules

if __name__ == '__main__':
    metadata_spider(sys.argv[1])
