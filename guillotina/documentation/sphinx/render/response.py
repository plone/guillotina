from docutils import nodes


HTTP_STATUS_CODES = {
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi Status',
    226: 'IM Used',              # see RFC 3229
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',     # unused
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",        # see RFC 2324
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    426: 'Upgrade Required',
    429: 'Too Many Requests',
    449: 'Retry With',           # proprietary MS extension
    451: 'Unavailable For Legal Reasons',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    507: 'Insufficient Storage',
    510: 'Not Extended'
}

WEBDAV_STATUS_CODES = [207, 422, 423, 424, 507]


def render_response(code, message):
    code = int(code.strip())

    if code == 226:
        url = 'http://www.ietf.org/rfc/rfc3229.txt'
    elif code == 418:
        url = 'http://www.ietf.org/rfc/rfc2324.txt'
    elif code == 429:
        url = 'http://tools.ietf.org/html/rfc6585#section-4'
    elif code == 449:
        url = 'http://msdn.microsoft.com/en-us/library/dd891478(v=prot.10).aspx'
    elif code in WEBDAV_STATUS_CODES:
        url = 'http://tools.ietf.org/html/rfc4918#section-11.%d' % (
            WEBDAV_STATUS_CODES.index(code) + 1)
    elif code in HTTP_STATUS_CODES:
        url = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html' \
              '#sec10.' + ('%d.%d' % (code // 100, 1 + code % 100))
    else:
        url = ''
    status = HTTP_STATUS_CODES.get(code, '')
    text = '%d %s' % (code, status)
    # return addnodes.download_reference(text, text, refuri=url, reftarget='_blank')
    return nodes.reference(text, text, refuri=url)
    # return addnodes.desc_annotation(text, text)
