# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import json
import logging
import datetime
import hashlib
import random
import string
import core.config as config
from core.transition import httpstatus
from functools import wraps

logg = logging.getLogger(__name__)

TESTING = config.get("host.type") == "testing"


template_exception2xml = u'''
<?xml version='1.0' encoding='utf8'?>
<response status="fail" retrievaldate="%(iso_datetime_now)s">
  <errormsg>%(errormsg)s</errormsg>
</response>
'''

template_exception2json = json.dumps({"status": "fail",
                              "retrievaldate": "%(iso_datetime_now)s",
                              "errormsg": "%(errormsg)s",
                              })

template_exception2csv = u'errormsg\n%(errormsg)s'

template_exception2template_test = template_exception2csv

template_exception2rss = template_exception2xml

# {'format_name': [template, mime-type]}
supported_formats = { 'xml': [template_exception2xml, 'text/xml'],
    'json': [template_exception2json, 'application/json'],
    'csv': [template_exception2csv, 'text/csv'],
    'template_test': [template_exception2template_test, 'text/plain'],
    'rss': [template_exception2rss, 'application/rss+xml'],
}


def dec_handle_exception(func):
    if TESTING:
        return func
    @wraps(func)
    def wrapper(req):
        try:
            http_status_code = func(req)
            return http_status_code
        except Exception, e:
            iso_datetime_now = datetime.datetime.now().isoformat()
            errormsg = str(e)
            hashed_errormsg = hashlib.md5(errormsg).hexdigest()[0:6]
            random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            XID = u"%s__%s__%s" % (iso_datetime_now, hashed_errormsg, random_string)
            logg.exception(u"exception (XID=%r) while handling request %r, %r" % (XID, req.path, req.params))
            response_format = req.params.get('format', '').lower()
            response_template, response_mimetype = supported_formats.get(response_format, supported_formats.get('xml'))
            req.reply_headers['Content-Type'] = response_mimetype
            response = response_template % dict(iso_datetime_now=iso_datetime_now, errormsg=u"%s: %s" % (XID, errormsg))
            response = response.strip()  # remove whitespaces at least from xml response
            req.setStatus(httpstatus.HTTP_INTERNAL_SERVER_ERROR)
            req.write(response)
            return None  # do not send status code 500, ..., athana would overwrite response
    return wrapper
