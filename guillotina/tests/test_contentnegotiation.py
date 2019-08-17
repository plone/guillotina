from guillotina.contentnegotiation import get_acceptable_content_types


class DummyRequest:
    def __init__(self, ct):
        self.headers = {"ACCEPT": ct}


def test_negotiate_html_accept_header():
    cts = get_acceptable_content_types(
        DummyRequest(
            "text/html,application/xhtml+xml,application/xml;" "q=0.9,image/webp,image/apng,*/*;q=0.8"
        )
    )
    assert cts == ["text/html", "application/xhtml+xml", "image/webp", "image/apng", "application/xml", "*/*"]


def test_order_weight_of_content_type_accept():
    cts = get_acceptable_content_types(
        DummyRequest(
            "text/html;q=0.1,application/xhtml+xml,application/xml;" "q=0.9,image/webp,image/apng,*/*;q=0.8"
        )
    )
    assert cts == ["application/xhtml+xml", "image/webp", "image/apng", "application/xml", "*/*", "text/html"]


def test_negotiate_complex_accept_header():
    cts = get_acceptable_content_types(
        DummyRequest(
            "application/vnd.google.protobuf;"
            "proto=io.prometheus.client.MetricFamily;"
            "encoding=delimited;q=0.7,text/plain;"
            "version=0.0.4;q=0.3,*/*;q=0.1"
        )
    )
    assert cts[0] == "application/vnd.google.protobuf"
    assert cts[1] == "text/plain"
    assert cts[2] == "*/*"


def test_equality_accept_header():
    cts = get_acceptable_content_types(
        DummyRequest(
            "text/html,application/xhtml+xml,application/xml;" "q=0.9,image/webp,image/apng,*/*;q=0.8"
        )
    )
    cts2 = get_acceptable_content_types(
        DummyRequest(
            "text/html,application/xhtml+xml,application/xml;" "q=0.9,image/webp,image/apng,*/*;q=0.8"
        )
    )
    assert cts == cts2


def test_ties_are_sorted_correctly():
    cts = get_acceptable_content_types(
        DummyRequest(
            "text/foobar;q=0.7,text/html,application/xhtml+xml;q=0.7,"
            "application/xml;q=0.9,image/webp,image/apng;q=0.7,*/*;q=0.6"
        )
    )
    assert cts == [
        "text/html",
        "image/webp",
        "application/xml",
        "text/foobar",
        "application/xhtml+xml",
        "image/apng",
        "*/*",
    ]
