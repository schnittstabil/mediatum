
import json
import logging
import datetime
from functools import wraps

logg = logging.getLogger(__name__)


template_exception2xml = '''
<?xml version='1.0' encoding='utf8'?>
<response status="fail" retrievaldate="%(iso_datetime_now)s">
  <errormsg>%(errormsg)s</errormsg>
</response>
'''

template_exception2json = json.dumps({"status": "fail",
                              "retrievaldate": "%(iso_datetime_now)s",
                              "errormsg": "%(errormsg)s",
                              })

template_exception2csv = 'errormsg\n%(errormsg)s'

template_exception2template_test = template_exception2csv

template_exception2rss = template_exception2xml


supported_formats = { 'xml': [template_exception2xml, 'text/xml'],
    'json': [template_exception2json, 'application/json'],
    'csv': [template_exception2csv, 'text/csv'],
    'template_test': [template_exception2template_test, 'text/plain'],
    'rss': [template_exception2rss, 'application/rss+xml'],
}


def dec_handle_exception(func):
    @wraps(func)
    def wrapper(req):
        print req, req.params
        try:
            http_status_code = func(req)
            return http_status_code
        except Exception, e:
            logg.exception(u"error while handling request %r, %r" % (req.path, req.params))
            response_format = req.params.get('format', '').lower()
            response_template, response_mimetype = supported_formats.get(response_format, supported_formats.get('xml'))
            req.reply_headers['Content-Type'] = response_mimetype
            iso_datetime_now = datetime.datetime.now().isoformat()
            errormsg = str(e)
            response = response_template % dict(iso_datetime_now=iso_datetime_now, errormsg=errormsg)
            response = response.strip()  # remove whitespaces for at least from xml response
            req.write(response)
            return '501'  # internal server error: 500
    return wrapper
