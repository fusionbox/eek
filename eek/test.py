from spider import *

def test_encoding():
    assert encoding_from_content_type('text/html; charset=utf-8') == 'utf-8'
    assert not encoding_from_content_type('text/html')


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
