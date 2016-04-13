"""
 mediatum - a multimedia content repository

 Copyright (C) 2007 Arne Seifert <seiferta@in.tum.de>
 Copyright (C) 2007 Matthias Kramm <kramm@in.tum.de>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from core.translation import translate, lang
from core.database.postgres.permission import AccessRuleset, NodeToAccessRuleset
from core import db
import logging

logg = logging.getLogger(__name__)
q = db.query


def ruleset_is_private_to_node(ruleset):
    """If this ruleset is the exclusive private ruleset for node n
    n.id is returned,
    otherwise None is returned
    """
    nids = q(NodeToAccessRuleset.nid).filter_by(ruleset_name=ruleset.name).filter_by(private=True).all()
    if not nids:
        return None
    elif len(nids) == 1:
        return nids[0][0]
    else:
        msg = u"data integrity error (?): ruleset %r is 'private' to more than one (%d) node" % (ruleset.name,
                                                                                                 len(nids))
        logg.warning(msg)
        raise ValueError(msg)


def makeList(req, own_ruleset_assocs, inherited_ruleset_assocs, special_ruleset, special_rule_assocs,
             rulesetnamelist, private_ruleset_names, rule_type=''):

    #            (req, not_inherited_ruleset_names, inherited_ruleset_names, additional_rules_inherited=[],
    #         additional_rules_not_inherited=[], rule_type=""):
    already_shown_left = {}  # ruleset names in left handside lists will not be shown on the right side

    # for filling val_right
    #rulesetnamelist = [t[0] for t in q(AccessRuleset.name).order_by(AccessRuleset.name).all()]
    #private_rulset_names = [t[0] for t in q(NodeToAccessRuleset.ruleset_name).filter_by(private=True).all()]
    #rulesetnamelist = [rulesetname for rulesetname in rulesetnamelist if not rulesetname in private_rulset_names]

    val_left = []
    val_right = []

    # inherited rulesets
    inherited_ruleset_names = [r.ruleset_name for r in inherited_ruleset_assocs]
    for rulesetname in inherited_ruleset_names:
        if rulesetname in private_ruleset_names:
            val_left.append(
                """<optgroup label="%s"></optgroup>""" % (translate("edit_acl_special_rule", lang(req))))
        else:
            val_left.append("""<optgroup label="%s"></optgroup>""" % rulesetname)
            already_shown_left[rulesetname] = 1

    # node level rulesets (not inherited)
    own_ruleset_names = [r.ruleset_name for r in own_ruleset_assocs]
    for rulesetname in own_ruleset_names:
        if rulesetname in private_ruleset_names:
            entry_text = translate("edit_acl_special_rule", lang(req))
            val_left.append(
                """<option value="__special_rule__">%s</optgroup>""" % (entry_text, ))
        else:
            val_left.append("""<option value="%s">%s</option>""" % (rulesetname, rulesetname))
            already_shown_left[rulesetname] = 1

    for rulesetname in rulesetnamelist:
        if rulesetname not in already_shown_left:
            val_right.append("""<option value="%s">%s</option>""" % (rulesetname, rulesetname))

    res = {"name": rule_type, "val_left": "".join(val_left), "val_right": "".join(val_right), "type": rule_type}

    return res
