# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import schema.schema

def test_filter_masks(content_node_with_mdt):
    node = content_node_with_mdt
    masks = node.metadatatype.filter_masks().all()
    assert len(masks) == 4


def test_filter_masks_language(content_node_with_mdt):
    node = content_node_with_mdt
    masks = node.metadatatype.filter_masks(language="en").all()
    # should get only english masks, no language-independent
    assert len(masks) == 2
    for mask in masks:
        assert mask.language == "en"


def test_filter_masks_language_type(content_node_with_mdt):
    node = content_node_with_mdt
    masks = node.metadatatype.filter_masks(masktype="testmasktype", language="en").all()
    assert len(masks) == 1
    assert masks[0]["masktype"] == "testmasktype"
    
    
def test_update_node(session, req, editor_user, some_node, simple_mask_with_maskitems):
    mask = simple_mask_with_maskitems
    node = some_node
    schema.schema.init()
    req.form["testattr"] = u"updated"
    req.form["newattr"] = u"new"
    req.form["nodename"] = u"new_name"
    mask.update_node(node, req)
    assert node["testattr"] == u"updated"
    assert node["newattr"] == u"new"
    assert node.name == u"new_name"