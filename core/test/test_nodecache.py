# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2014 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from pytest import fixture

from core import db
from core.test.asserts import assert_node
from core.permission import get_or_add_everybody_rule
q = db.query


@fixture(autouse=True)
def default_data(default_data):
    return default_data


def test_get_root():
    from core.systemtypes import Root
    n = q(Root).one()
    assert_node(n,
                name="root",
                type="root",
                schema=None)


def test_get_collections():
    from contenttypes import Collections
    n = q(Collections).one()
    assert_node(n,
                name="collections",
                type="collections",
                schema="collection",
                label="Collections")

    # collections is public by default, so it must have the everybody rule
    everybody_rule = get_or_add_everybody_rule()
    assert n.access_rule_assocs[0].rule is everybody_rule

