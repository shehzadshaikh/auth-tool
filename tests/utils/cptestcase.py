# -*- coding: utf-8 -*-
from StringIO import StringIO
import unittest
import urllib

import cherrypy

# Not strictly speaking mandatory but just makes sense
cherrypy.config.update({'environment': "test_suite"})

# This is mandatory so that the HTTP server isn't started
# if you need to actually start (why would you?), simply
# subscribe it back.
cherrypy.server.unsubscribe()

# simulate fake socket address... they are irrelevant in our context
local = cherrypy.lib.httputil.Host('127.0.0.1', 50000, "")
remote = cherrypy.lib.httputil.Host('127.0.0.1', 50001, "")

__all__ = ['BaseCherryPyTestCase']

class BaseCherryPyTestCase(unittest.TestCase):
    def request(self, path='/',
                method='GET',
                app_path='',
                scheme='http',
                proto='HTTP/1.1',
                body=None,
                qs=None,
                headers=None,
                **kwargs):
        """
        CherryPy does not have a facility for serverless unit testing.
        However this recipe demonstrates a way of doing it by
        calling its internal API to simulate an incoming request.
        This will exercise the whole stack from there.

        Remember a couple of things:

        * CherryPy is multithreaded. The response you will get
            from this method is a thread-data object attached to
            the current thread. Unless you use many threads from
            within a unit test, you can mostly forget
            about the thread data aspect of the response.

        * Responses are dispatched to a mounted application's
            page handler, if found. This is the reason why you
            must indicate which app you are targetting with
            this request by specifying its mount point.

        You can simulate various request settings by setting
        the `headers` parameter to a dictionary of headers,
        the request's `scheme` or `protocol`.

        .. seealso: http://docs.cherrypy.org/stable/refman/_cprequest.html#cherrypy._cprequest.Response
        """
        # This is a required header when running HTTP/1.1
        h = {'Host': '127.0.0.1'}

        # if we had some data passed as the request entity
        # let's make sure we have the content-length set
        fd = None
        if body is not None:
            h['content-length'] = '{0}'.format(len(str(body)))
            fd = StringIO(body)

        if headers is not None:
            h.update(headers)

        # Get our application and run the request against it
        app = cherrypy.tree.apps.get(app_path)
        if not app:
            # XXX: perhaps not the best exception to raise?
            raise AssertionError("No application mounted at '{0}'".format(app_path))

        # Cleanup any previous returned response
        # between calls to this method
        app.release_serving()

        # Let's fake the local and remote addresses
        request, response = app.get_serving(local, remote, scheme, proto)
        try:
            h = [(k, v) for k, v in h.iteritems()]
            response = request.run(method, path, qs, proto, h, fd)
        finally:
            if fd:
                fd.close()
                fd = None

        if response.output_status.startswith('500'):
            print response.body
            raise AssertionError("Unexpected error")

        response.collapse_body()
        return request, response
