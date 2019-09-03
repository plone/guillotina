# pulled out of repoze.sendmail
from email import header
from email import utils


# From http://tools.ietf.org/html/rfc5322#section-3.6
ADDR_HEADERS = (
    "resent-from",
    "resent-sender",
    "resent-to",
    "resent-cc",
    "resent-bcc",
    "from",
    "sender",
    "reply-to",
    "to",
    "cc",
    "bcc",
)

PARAM_HEADERS = ("content-type", "content-disposition")


def cleanup_message(message, addr_headers=ADDR_HEADERS, param_headers=PARAM_HEADERS):
    """
    Cleanup a `Message` handling header and payload charsets.

    Headers are handled in the most sane way possible.  Address names
    are left in `ascii` if possible or encoded to `iso-8859-1` or `utf-8`
    and finally encoded according to RFC 2047 without encoding the
    address, something the `email` stdlib package doesn't do.
    Parameterized headers such as `filename` in the
    `Content-Disposition` header, have their values encoded properly
    while leaving the rest of the header to be handled without
    encoding.  Finally, all other header are left in `ascii` if
    possible or encoded to `iso-8859-1` or `utf-8` as a whole.

    The message is modified in place and is also returned in such a
    state that it can be safely encoded to ascii.
    """
    for key, value in message.items():
        if key.lower() in addr_headers:
            addrs = []
            for name, addr in utils.getaddresses([value]):
                best, encoded = best_charset(name)
                name = header.Header(name, charset=best, header_name=key).encode()
                addrs.append(utils.formataddr((name, addr)))
            value = ", ".join(addrs)
            message.replace_header(key, value)
        if key.lower() in param_headers:
            for param_key, param_value in message.get_params(header=key):
                if param_value:
                    best, encoded = best_charset(param_value)
                    if best == "ascii":
                        best = None
                    message.set_param(param_key, param_value, header=key, charset=best)
        else:
            best, encoded = best_charset(value)
            value = header.Header(value, charset=best, header_name=key).encode()
            message.replace_header(key, value)

    payload = message.get_payload()
    if payload and isinstance(payload, str):
        charset = message.get_charset()
        if not charset:
            charset, encoded = best_charset(payload)
            message.set_payload(payload, charset=charset)
    elif isinstance(payload, list):
        for part in payload:
            cleanup_message(part)

    return message


def encode_message(message, addr_headers=ADDR_HEADERS, param_headers=PARAM_HEADERS):
    """
    Encode a `Message` handling headers and payloads.

    Headers are handled in the most sane way possible.  Address names
    are left in `ascii` if possible or encoded to `iso-8859-1` or `utf-8`
    and finally encoded according to RFC 2047 without encoding the
    address, something the `email` stdlib package doesn't do.
    Parameterized headers such as `filename` in the
    `Content-Disposition` header, have their values encoded properly
    while leaving the rest of the header to be handled without
    encoding.  Finally, all other header are left in `ascii` if
    possible or encoded to `iso-8859-1` or `utf-8` as a whole.

    The return is a byte string of the whole message.
    """
    cleanup_message(message)
    return message.as_string().encode("ascii")


def best_charset(text):
    """
    Find the most human-readable and/or conventional encoding for unicode text.

    Prefers `ascii` or `iso-8859-1` and falls back to `utf-8`.
    """
    encoded = text
    for charset in "ascii", "iso-8859-1", "utf-8":
        try:
            encoded = text.encode(charset)
        except UnicodeError:
            pass
        else:
            return charset, encoded
