import calendar
from datetime import datetime


def utcnow():
    return datetime.utcnow()


def timestamp(dt):
    return int(calendar.timegm(dt.utctimetuple()))
