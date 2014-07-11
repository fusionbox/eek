import urlparse
import csv
import sys
import re
import collections
import time
import requests

from eek import robotparser  # this project's version
from bs4 import BeautifulSoup

try:
    import lxml
except ImportError:
    HTML_PARSER = None
else:
    HTML_PARSER = 'lxml'


encoding_re = re.compile("charset\s*=\s*(\S+?)(;|$)")
html_re = re.compile("text/html")
headers = ['url', 'title', 'description', 'keywords', 'allow', 'disallow',
           'noindex', 'meta robots', 'canonical', 'referer', 'status']

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


def beautify(response):
    content_type = response.headers['content-type']
    if content_type:
        if not html_re.search(content_type):
            raise NotHtmlException
        encoding = encoding_from_content_type(content_type)
    else:
        encoding = None
    try:
        return BeautifulSoup(
            response.content,
            features=HTML_PARSER,
            from_encoding=encoding,
        )
    except UnicodeEncodeError:
        raise NotHtmlException


def get_links(response):
    if 300 <= response.status_code < 400 and response.headers['location']:
        # redirect
        yield urlparse.urldefrag(
            urlparse.urljoin(response.url, response.headers['location'], False)
        )[0]
    try:
        html = beautify(response)
        for i in html.find_all('a', href=True):
            yield urlparse.urldefrag(urlparse.urljoin(response.url, i['href'], False))[0]
    except NotHtmlException:
        pass


def force_unicode(s):
    if isinstance(s, str):
        return unicode(s, encoding='utf-8')
    else:
        return s


def force_bytes(str_or_unicode):
    if isinstance(str_or_unicode, unicode):
        return str_or_unicode.encode('utf-8')
    else:
        return str_or_unicode


def get_pages(base, clerk, session=requests.session()):
    clerk.enqueue(base, base)
    base_domain = lremove(urlparse.urlparse(base).netloc, 'www.')
    for (url, referer) in clerk:
        url = force_bytes(url)
        referer = force_bytes(referer)
        response = session.get(
            url,
            headers={'Referer': referer, 'User-Agent': 'Fusionbox spider'},
            allow_redirects=False,
        )
        for link in get_links(response):
            parsed = urlparse.urlparse(link)
            if lremove(parsed.netloc, 'www.') == base_domain:
                clerk.enqueue(link, url)
        yield referer, response


def metadata_spider(base, output=sys.stdout, delay=0, insecure=False):
    writer = csv.writer(output)
    robots = robotparser.RobotFileParser(base + '/robots.txt')
    robots.read()
    writer.writerow(headers)

    session = requests.session()
    session.verify = not insecure
    for referer, response in get_pages(base, VisitOnlyOnceClerk(), session=session):
        rules = applicable_robot_rules(robots, response.url)

        robots_meta = canonical = title = description = keywords = ''
        try:
            html = beautify(response)
            robots_meta = ','.join(i['content'] for i in html.find_all('meta', {"name": "robots"}))
            try:
                canonical = html.find_all('link', {"rel": "canonical"})[0]['href']
            except IndexError:
                pass
            try:
                title = html.head.title.contents[0]
            except (AttributeError, IndexError):
                pass
            try:
                description = html.head.find_all('meta', {"name": "description"})[0]['content']
            except (AttributeError, IndexError, KeyError):
                pass
            try:
                keywords = html.head.find_all('meta', {"name": "keywords"})[0]['content']
            except (AttributeError, IndexError, KeyError):
                pass
        except NotHtmlException:
            pass

        writer.writerow(map(force_bytes, [
            response.url,
            title,
            description,
            keywords,
            ','.join(rules['allow']),
            ','.join(rules['disallow']),
            ','.join(rules['noindex']),
            robots_meta,
            canonical,
            referer,
            response.status_code,
        ]))

        if delay:
            time.sleep(delay)


def grep_spider(base, pattern, delay=0, insensitive=False, insecure=False):
    flags = 0
    if insensitive:
        flags |= re.IGNORECASE
    pattern = re.compile(pattern, flags)

    session = requests.session()
    session.verify = not insecure
    for referer, response in get_pages(base, VisitOnlyOnceClerk(), session=session):
        for line in response.content.split('\n'):
            if pattern.search(line):
                print u'%s:%s' % (force_unicode(response.url), force_unicode(line))
        if delay:
            time.sleep(delay)


def graphviz_spider(base, delay=0, insecure=False):
    print "digraph links {"
    session = requests.session()
    session.verify = not insecure
    for referer, response in get_pages(base, VisitOnlyOnceClerk(), session=session):
        for link in get_links(response):
            print '  "%s" -> "%s";' % (force_bytes(response.url), force_bytes(link))
            if delay:
                time.sleep(delay)
    print "}"


def applicable_robot_rules(robots, url):
    rules = collections.defaultdict(list)
    if robots.default_entry:
        rules[robots.default_entry.allowance(url)].append('*')
    for entry in robots.entries:
        rules[entry.allowance(url)].extend(entry.useragents)
    return rules
