from unittest import TestCase
import nose.tools

from spider import *

def test_encoding():
    assert encoding_from_content_type('text/html; charset=utf-8') == 'utf-8'
    assert not encoding_from_content_type('text/html')


class TestScraper(TestCase):
    def scrape_helper(self, html, links, title, description, keywords):
        bs = BeautifulSoup(html, convertEntities=BeautifulSoup.XML_ENTITIES)
        bs.base_url = 'http://example.com/'

        data = scrape_html(bs)
        assert set(data[0]) == set(links)
        assert data[1] == title
        assert data[2] == description
        assert data[3] == keywords

    def test_nothin(self):
        self.scrape_helper("""
        <html>
        </html>
        """,
        [],
        '',
        '',
        ''
        )

    def test_just_title(self):
        self.scrape_helper("""
        <html>
            <head>
                <title>test &amp;</title>
            </head>
        </html>
        """,
        [],
        'test &',
        '',
        ''
        )
        
    def test_description(self):
        self.scrape_helper("""
        <html>
            <head>
                <meta name="description" content="the description"/>
            </head>
        </html>
        """,
        [],
        '',
        'the description',
        ''
        )

    def test_keywords(self):
        self.scrape_helper("""
        <html>
            <head>
                <title>test</title>
                <meta name="description" content="the description"/>
                <meta name="keywords" content="the keywords"/>
            </head>
        </html>
        """,
        [],
        'test',
        'the description',
        'the keywords'
        )

    def test_links(self):
        self.scrape_helper("""
        <html>
        <body>
            <a href="/asdf">
            <a href="http://google.com/">
        </body>
        """,
        ['http://example.com/asdf', 'http://google.com/'],
        '',
        '',
        ''
        )

def test_url_task():
    assert len(set((UrlTask(('a', 'asdf')), UrlTask(('a', 'fdsa'))))) == 1
    assert len(set((UrlTask(('a', 'asdf')), UrlTask(('b', 'fdsa'))))) == 2


def test_visit_only_once_clerk():
    c = VisitOnlyOnceClerk()
    c.enqueue('a', 'a')
    for (url, referer) in c:
        assert url == 'a'
        assert referer == 'a'
        c.enqueue('a', 'b')
        c.enqueue('a', 'a')


## stub urllib for these?
def test_get_url():
    assert get_url('http://example.com/')

@nose.tools.raises(urllib2.URLError)
def test_get_url_404():
    get_url('http://fusionbox.com/asdfasdfajslkdjfalskdfjlaasdfaa/')

@nose.tools.raises(NotHtmlException)
def test_get_url_not_html():
    get_url('http://www.fusionbox.com/image/logo.gif')
