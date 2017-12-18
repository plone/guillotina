from guillotina.component import get_utility
from guillotina.interfaces import IContentNegotiation


def test_negotiate_html_accept_header(dummy_guillotina):
    np = get_utility(IContentNegotiation, 'content_type')
    ap = np.negotiate(
        accept='text/html,application/xhtml+xml,application/xml;'
               'q=0.9,image/webp,image/apng,*/*;q=0.8')
    assert str(ap.content_type) == 'text/html'


def test_negotiate_complex_accept_header(dummy_guillotina):
    np = get_utility(IContentNegotiation, 'content_type')
    ap = np.negotiate(
        accept='application/vnd.google.protobuf;'
               'proto=io.prometheus.client.MetricFamily;'
               'encoding=delimited;q=0.7,text/plain;'
               'version=0.0.4;q=0.3,*/*;q=0.1')
    assert str(ap.content_type) == 'text/plain'


def test_equality_accept_header(dummy_guillotina):
    np = get_utility(IContentNegotiation, 'content_type')
    ap = np.negotiate(
        accept='text/html,application/xhtml+xml,application/xml;'
               'q=0.9,image/webp,image/apng,*/*;q=0.8')
    ap2 = np.negotiate(
        accept='text/html,application/xhtml+xml,application/xml;'
               'q=0.9,image/webp,image/apng,*/*;q=0.8')
    assert ap == ap2
