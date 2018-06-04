from guillotina.contentnegotiation import get_acceptable_content_types


class DummyRequest:

    def __init__(self, ct):
        self.headers = {
            'ACCEPT': ct
        }


def test_negotiate_html_accept_header(dummy_guillotina):
    cts = get_acceptable_content_types(DummyRequest(
        'text/html,application/xhtml+xml,application/xml;'
        'q=0.9,image/webp,image/apng,*/*;q=0.8'))
    assert 'text/html' in cts


def test_negotiate_complex_accept_header(dummy_guillotina):
    cts = get_acceptable_content_types(DummyRequest(
        'application/vnd.google.protobuf;'
        'proto=io.prometheus.client.MetricFamily;'
        'encoding=delimited;q=0.7,text/plain;'
        'version=0.0.4;q=0.3,*/*;q=0.1'))
    assert 'text/plain' in cts


def test_equality_accept_header(dummy_guillotina):
    cts = get_acceptable_content_types(DummyRequest(
        'text/html,application/xhtml+xml,application/xml;'
        'q=0.9,image/webp,image/apng,*/*;q=0.8'))
    cts2 = get_acceptable_content_types(DummyRequest(
        'text/html,application/xhtml+xml,application/xml;'
        'q=0.9,image/webp,image/apng,*/*;q=0.8'))
    assert cts == cts2
