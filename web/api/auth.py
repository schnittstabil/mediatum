# -*- coding: utf-8 -*-
import functools
import logging

from flask import g, request, jsonify

from core import db, User
from core.auth import authenticate_user_credentials

logg = logging.getLogger(__name__)
q = db.query


class HTTPBasicAuth(object):
    def _authenticate(self):
        resp = jsonify({'error': 'Login Required'})
        resp.status_code = 401
        resp.headers['WWW-Authenticate'] = 'Basic realm="mediaTUM API"'
        return resp

    def _forbidden(self):
        return jsonify({'error': 'Forbidden'}), 403

    def _login(self, login_name, password):
        user = q(User).filter_by(login_name=login_name).first()
        if user is None:
            return None
        if authenticate_user_credentials(login_name, password, request) is None:
            return None
        return user

    def login_required(self, f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth:
                return self._authenticate()

            user = self._login(auth.username, auth.password)
            if user is None:
                return self._authenticate()

            g.user = user
            return f(*args, **kwargs)
        return decorated
