import BaseHTTPServer
import threading
from SimpleHTTPServer import SimpleHTTPRequestHandler

HandlerClass = SimpleHTTPRequestHandler
ServerClass  = BaseHTTPServer.HTTPServer
Protocol     = "HTTP/1.0"

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
