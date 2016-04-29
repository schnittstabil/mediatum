# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
from munch import Munch
from core.permission import get_or_add_everybody_rule
from core import AccessRulesetToRule


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


def make_node_public(node, ruletype=u"all"):
    er = get_or_add_everybody_rule()

    def _add(ruletype):
        special_ruleset = node.get_or_add_special_access_ruleset(ruletype)
        rsa = AccessRulesetToRule(rule=er)
        special_ruleset.rule_assocs.append(rsa)

    if ruletype == "all":
        for ruletype in (u"read", u"write", u"data"):
            _add(ruletype)
    else:
        _add(ruletype)

