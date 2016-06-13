# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
    
    Various handlers for testing handlers.
"""
from __future__ import absolute_import


def error(req):
    raise Exception("this is a test!")