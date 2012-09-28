import BaseHTTPServer
import threading
from SimpleHTTPServer import SimpleHTTPRequestHandler

HandlerClass = SimpleHTTPRequestHandler
ServerClass = BaseHTTPServer.HTTPServer
Protocol = "HTTP/1.0"

port = 8888
server_address = ('127.0.0.1', port)

HandlerClass.protocol_version = Protocol
httpd = ServerClass(server_address, HandlerClass)

sa = httpd.socket.getsockname()

httpd_thread = threading.Thread(target=httpd.serve_forever)
httpd_thread.setDaemon(True)
print "Serving HTTP on", sa[0], "port", sa[1], "..."
httpd_thread.start()

from unittest import TestCase
import tempfile
import requests
import csv
import sys
from StringIO import StringIO
sort_by_url = lambda k: k['url']


class TestBeautify(TestCase):
    class MockResponse(object):
        def __init__(self, content_type, content):
            self.headers = {'content-type': content_type}
            self.content = content

    def test_return_no_encoding(self):
        from eek.spider import beautify
        response = self.MockResponse('text/html',
                                     '<!doctype html><p>Hello</p>')
        result = beautify(response)
        self.assertIsNone(result.fromEncoding)

    def test_return_not_none_encoding(self):
        from eek.spider import beautify
        response = self.MockResponse('text/html; charset=utf-8',
                                     '<!doctype html><p>Hello</p>')
        result = beautify(response)
        self.assertIsNotNone(result.fromEncoding)

    def test_raise_NotHtmlException_on_messed_up_content_type(self):
        from eek.spider import beautify, NotHtmlException
        response = self.MockResponse('foo',
                                     '<!doctype html><p>Hello</p>')
        with self.assertRaises(NotHtmlException):
            beautify(response)


class TestSpiderUtilities(TestCase):

    def test_encoding_from_content_type_none(self):
        from eek.spider import encoding_from_content_type
        self.assertIsNone(encoding_from_content_type('text/html'))

    def test_encoding_from_content_type_with_charset(self):
        from eek.spider import encoding_from_content_type
        self.assertEquals(
            encoding_from_content_type('text/html; charset=utf-8'),
            'utf-8')

    def test_lremove_prefix_exists(self):
        from eek.spider import lremove
        self.assertEquals(lremove('www.foo.com', 'www.'), 'foo.com')

    def test_lremove_prefix_not_exists(self):
        from eek.spider import lremove
        self.assertEquals(lremove('www.foo.com', 'eggs'), 'www.foo.com')

    def test_force_unicode_is_string_instance(self):
        from eek.spider import force_unicode
        uni_string = force_unicode('spam')
        self.assertIsInstance(uni_string, unicode)
        self.assertEquals(uni_string, u'spam')

    def test_force_unicode_not_string_instance(self):
        from eek.spider import force_unicode
        result = force_unicode(5)
        self.assertNotIsInstance(result, unicode)
        self.assertEquals(result, 5)
        result = force_unicode(None)
        self.assertNotIsInstance(result, unicode)
        self.assertEquals(result, None)

    def test_force_bytes_unicode_literal(self):
        from eek.spider import force_bytes
        self.assertEquals(force_bytes(u'\u2603'), '\xe2\x98\x83')

    def test_force_bytes_string(self):
        from eek.spider import force_bytes
        self.assertEquals(force_bytes('\xe2\x98\x83'), '\xe2\x98\x83')


class FunctionalTests(TestCase):
    base = 'http://localhost:%d/tests/html-files' % port

    def setUp(self):
        self.tmp = tempfile.TemporaryFile()

    def tearDown(self):
        self.tmp.close()

    def test_testsetup(self):
        assert requests.get(self.base).status_code == 200

    def test_metaspider(self):
        from eek import spider
        pages = [dict([(h, '') for h in spider.headers]) for x in range(4)]
        for p in pages:
            p['referer'] = self.base + '/index.html'
            p['status'] = '200'
        pages[0]['url'] = self.base + '/index.html'
        pages[0]['keywords'] = 'my_keywords'
        pages[0]['title'] = 'Index'
        pages[0]['description'] = 'my_description'
        pages[0]['meta robots'] = 'arst'
        pages[1]['url'] = self.base + '/a.html'
        pages[2]['url'] = self.base + '/b.html'
        pages[3]['url'] = self.base + '/c.html'
        pages = sorted(pages, key=sort_by_url)
        spider.metadata_spider(self.base + '/index.html', output=self.tmp)
        self.tmp.seek(0)
        result = sorted(list(csv.DictReader(self.tmp)), key=sort_by_url)
        self.assertEquals(pages, result)

    def test_grepspider(self):
        from eek import spider
        sys.stdout = StringIO()
        spider.grep_spider(self.base + '/index.html', 'Found me')
        self.assertEquals(sys.stdout.getvalue(), self.base + '/b.html:Found me\n')

    def test_graphvizspider(self):
        from eek import spider
        sys.stdout = StringIO()
        spider.graphviz_spider(self.base + '/index.html')
        graphiz_assertion = """digraph links {{
  "{base}/index.html" -> "{base}/a.html";
  "{base}/index.html" -> "{base}/b.html";
  "{base}/index.html" -> "{base}/c.html";
}}
""".format(base=self.base)
        self.assertEquals(sys.stdout.getvalue(), graphiz_assertion)
