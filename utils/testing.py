# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from munch import Munch


def make_files_munch(node):
    d = {}
    for f in node.files:
        existing = d.get(f.filetype)
        if not existing:
            d[f.filetype] = f
        elif isinstance(existing, dict):
            existing[f.mimetype] = f
        else:
            d[f.filetype] = {f2.mimetype: f2 for f2 in [existing, f]}

    return Munch(d)
