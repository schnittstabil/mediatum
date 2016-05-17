# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import pytest
from pytest import raises
from web.frontend.search import simple_search, NoSearchResult
from utils.testing import make_node_public
from sqlalchemy.orm.exc import NoResultFound


def assert_no_searchresult(res, readable_query=None, container=None, error=None):
    assert isinstance(res, NoSearchResult)
    if readable_query:
        assert res.query == readable_query
    if container:
        assert res.container == container
    if error:
        assert res.error == error


def test_simple_search(session, req, container_node):
    make_node_public(container_node)
    req.args["query"] = readable_query = u"simple"
    session.flush()
    req.args["id"] = container_node.id
    res = simple_search(req)
    assert_no_searchresult(res, readable_query, container_node, error=False)


@pytest.mark.parametrize("searchquery", [
    u"Haus AND Hof",
    u"Haus OR Hof",
    u"!Haus AND !Hof",
    u"!Haus AND !Hof AND Blah",
    u"!Haus AND !Hof AND Garten",
    u"!Haus AND (!Hof AND Garten)",
    u'"',
    u'""',
    u'"blah',
    u'&',
    u'blah&',
    u'^*°°°^%&|!',
])
def test_simple_search_special_chars(session, req, container_node, searchquery):
    make_node_public(container_node)
    req.args["query"] = readable_query = searchquery
    session.flush()
    req.args["id"] = container_node.id
    res = simple_search(req)
    assert_no_searchresult(res, readable_query, container_node, error=True)


def test_simple_search_no_access(session, req, container_node):
    req.args["query"] = u"doesntmatter"
    session.flush()
    req.args["id"] = container_node.id
    with raises(NoResultFound):
        simple_search(req)

