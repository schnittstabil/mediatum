# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from web.edit.modules.metadata import _handle_edit_metadata
from schema.test.factories import MaskFactory, TextMetafieldFactory, FieldMaskitemFactory
from utils.testing import make_node_public
from schema import schema


def test_handle_edit_metadata_new_tagged_version(session, req, editor_user, some_node):
    nodes = [some_node]
    node = some_node
    make_node_public(some_node)
    schema.init()
    req.session["user_id"] = editor_user.id
    req.params["testattr"] = u"updated"
    req.params["generate_new_version"] = 1
    mask = MaskFactory()
    maskitem = FieldMaskitemFactory(name=u"testattr")
    metafield = TextMetafieldFactory(name=u"testattr")
    maskitem.metafield = metafield
    mask.children.append(maskitem)
    session.flush()
    res = _handle_edit_metadata(req, mask, nodes)
    assert res
    assert node["testattr"] == u"updated"