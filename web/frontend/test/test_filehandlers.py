# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from web.frontend.filehandlers import fetch_archived
from core.archive import Archive


def test_fetch_archived(req, session, fake_archive, content_node):
    node = content_node
    node.system_attrs[u"archive_path"] = u"testpath"
    node.system_attrs[u"archive_type"] = u"test"
    session.flush()
    req.path = u"/archive/{}".format(node.id)
    assert fake_archive.get_state(node) == Archive.NOT_PRESENT
    fetch_archived(req)
    assert fake_archive.get_state(node) == Archive.PRESENT
