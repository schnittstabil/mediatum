
import json
import logging
from functools import wraps

logg = logging.getLogger(__name__)


def getNow():
    import datetime, time
    now = datetime.datetime.now().isoformat()
    #now = now.replace('T','_').replace(':','-')
    #now = now.split('.')[0]
    return now


_exception2xml = '''
<?xml version='1.0' encoding='utf8'?>
<response status="fail" retrievaldate="%(_now)s">
  <errormsg>%(_errormsg)s</errormsg>
</response>
'''

_exception2json = json.dumps({"status": "fail",
                              "retrievaldate": "%(_now)s",
                              "errormsg": "%(_errormsg)s",
                              })

_exception2csv = 'errormsg\n%(_errormsg)s'

_exception2template_test = _exception2csv

_exception2rss = _exception2xml


supported_formats = { 'xml': [_exception2xml, 'text/xml'],
    'json': [_exception2json, 'application/json'],
    'csv': [_exception2csv, 'text/csv'],
    'template_test': [_exception2template_test, 'text/plain'],
    'rss': [_exception2rss, 'application/rss+xml'],
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
            _now = getNow()
            _errormsg = str(e)
            response = response_template % dict(_now=_now, _errormsg=_errormsg)
            response = response.strip()  # remove whitespaces for at least from xml response
            req.write(response)
            return '501'  # internal server error: 500
    return wrapper


def dec_handle_exception_gen(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print args, kwargs
        try:
            res = apply(func, args, kwargs)
            print 'decorator of service handler saw no exception'
            return res
        except Exception,e:
            print 'decorator of service handler handled exception %s' % e
            raise e
    return wrapper