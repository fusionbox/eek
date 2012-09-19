import urlparse
import csv
import sys
import re
import collections
import time
import requests
import gevent
from gevent import util, queue, monkey
monkey.patch_all(thread=False)

from eek import robotparser  # this project's version
from eek.BeautifulSoup import BeautifulSoup


encoding_re = re.compile("charset\s*=\s*(\S+?)(;|$)")
html_re = re.compile("text/html")
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



class VisitOnlyOnceClerk(object):
    def __init__(self):
        self.visited = set()
        self.to_visit = queue.JoinableQueue()
    def enqueue(self, url, referer):
        if not url in self.visited:
            self.to_visit.put((url, referer))
            self.visited.add(url)
    def __bool__(self):
        return bool(self.to_visit)
    def __iter__(self):
        for url, referer in self.to_visit:
            yield (url, referer)
    def task_done(self):
        self.to_visit.task_done()


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
                fromEncoding=encoding,
                convertEntities=BeautifulSoup.HTML_ENTITIES)
    except UnicodeEncodeError:
        raise NotHtmlException


def get_links(response):
    if 300 <= response.status_code < 400 and response.headers['location']:
        # redirect
        yield urlparse.urldefrag(urlparse.urljoin(response.url, response.headers['location'], False))[0]
    try:
        html = beautify(response)
        for i in html.findAll('a', href=True):
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


def fetcher_thread(clerk, results_queue, base_domain, session_settings):
    session = requests.session(**session_settings)
    for url, referer in clerk:
        url = force_bytes(url)
        referer = force_bytes(referer)
        response = session.get(
                url,
                headers={'Referer': referer, 'User-Agent': 'Fusionbox spider'},
                allow_redirects=False)
        for link in get_links(response):
            parsed = urlparse.urlparse(link)
            if lremove(parsed.netloc, 'www.') == base_domain:
                clerk.enqueue(link, url)
        results_queue.put((referer, response))
        clerk.task_done()


def get_pages(base, clerk, session=requests.session(), workers=2):
    base_domain = lremove(urlparse.urlparse(base).netloc, 'www.')
    results_queue = queue.Queue()
    clerk.enqueue(base, base)

    for w in range(workers):
        gevent.spawn(fetcher_thread, clerk, results_queue, base_domain)

    for i in results_queue:
        yield i
        if (clerk.to_visit.unfinished_tasks == 0 and clerk.to_visit.empty() and
            results_queue.empty()):
            raise StopIteration


def metadata_spider(base, output=sys.stdout, delay=0, insecure=False):
    writer = csv.writer(output)
    robots = robotparser.RobotFileParser(base + '/robots.txt')
    robots.read()
    writer.writerow(['url', 'title', 'description', 'keywords', 'allow', 'disallow',
                     'noindex', 'meta robots', 'canonical', 'referer', 'status'])

    for referer, response in get_pages(base,
                                       VisitOnlyOnceClerk(),
                                       session_settings={'verify': not insecure}):
        rules = applicable_robot_rules(robots, response.url)

        robots_meta = canonical = title = description = keywords = ''
        try:
            html = beautify(response)
            robots_meta = ','.join(i['content'] for i in html.findAll('meta', {"name": "robots"}))
            try:
                canonical = html.findAll('link', {"rel": "canonical"})[0]['href']
            except IndexError:
                pass
            try:
                title = html.head.title.contents[0]
            except (AttributeError, IndexError):
                pass
            try:
                description = html.head.findAll('meta', {"name": "description"})[0]['content']
            except (AttributeError, IndexError, KeyError):
                pass
            try:
                keywords = html.head.findAll('meta', {"name": "keywords"})[0]['content']
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

    for referer, response in get_pages(base,
                                       VisitOnlyOnceClerk(),
                                       session_settings={'verify': not insecure}):
        for line in response.content.split('\n'):
            if pattern.search(line):
                print u'%s:%s' % (force_unicode(response.url), force_unicode(line))
        if delay:
            time.sleep(delay)


def graphviz_spider(base, delay=0, insecure=False):
    print "digraph links {"
    for referer, response in get_pages(base,
                                       VisitOnlyOnceClerk(),
                                       session_settings={'verify': not insecure}):
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
