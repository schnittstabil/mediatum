# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2015 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
import logging
import json
from core import db, Node, User, UserGroup
from core.database.postgres.permission import NodeToAccessRule, NodeToAccessRuleset, EffectiveNodeToAccessRuleset, AccessRule, AccessRuleset

from core.transition import httpstatus, current_user
from web.common.acl_editor_web import makeList
from web.common.accessuser_editor_web import makeUserList, decider_is_private_user_group_access_rule

from utils.utils import dec_entry_log

q = db.query
s = db.session

logg = logging.getLogger(__name__)
rule_types = ["read", "write", "data"]


def getInformation():
    return {"version": "1.0", "system": 0}


def get_user_for_login_name(login_name):
    cand = q(User).filter_by(login_name=login_name).scalar()
    return cand


# from bin/mediatumipython.py (make_info_producer_access_rules)
def make_access_rules_info_dict(node, ruletype):
    rule_assocs = node.access_rule_assocs.filter_by(ruletype=ruletype).all()
    own_ruleset_assocs = node.access_ruleset_assocs.filter_by(ruletype=ruletype).all()
    effective_ruleset_assocs = node.effective_access_ruleset_assocs.filter(
        EffectiveNodeToAccessRuleset.c.ruletype == ruletype).all()
    inherited_ruleset_assocs = set(effective_ruleset_assocs) - set(own_ruleset_assocs)

    effective_rulesets = [rsa.ruleset for rsa in effective_ruleset_assocs]
    rule_assocs_in_rulesets = [r for rs in effective_rulesets for r in rs.rule_assocs]

    def assoc_filter(assocs, to_remove):

        def _f(a):
            for rem in to_remove:
                if a.rule == rem.rule and a.invert == rem.invert and a.blocking == rem.blocking:
                    return False
            return True

        return [a for a in assocs if _f(a)]

    remaining_rule_assocs = assoc_filter(rule_assocs, rule_assocs_in_rulesets)
    special_ruleset = node.get_special_access_ruleset(ruletype)
    special_rule_assocs = special_ruleset.rule_assocs if special_ruleset else []
    res_dict = {
        'node': node,
        'rulesets_not_inherited': [rs.to_dict() for rs in own_ruleset_assocs],
        'rulesets_inherited': [rs.to_dict() for rs in inherited_ruleset_assocs],
        'additional_rules': [r.to_dict() for r in remaining_rule_assocs],
        'own_ruleset_assocs': own_ruleset_assocs,
        'inherited_ruleset_assocs': inherited_ruleset_assocs,
        'special_ruleset': special_ruleset,
        'special_rule_assocs': special_rule_assocs,
    }

    return res_dict


# from bin/mediatumipython.py (make_info_producer_access_rules)
def get_access_rules_info(node, ruletype):
    rule_assocs = node.access_rule_assocs.filter_by(ruletype=ruletype).all()
    own_ruleset_assocs = node.access_ruleset_assocs.filter_by(ruletype=ruletype).all()
    effective_ruleset_assocs = node.effective_access_ruleset_assocs.filter(
        EffectiveNodeToAccessRuleset.c.ruletype == ruletype).all()
    inherited_ruleset_assocs = set(effective_ruleset_assocs) - set(own_ruleset_assocs)

    effective_rulesets = [rsa.ruleset for rsa in effective_ruleset_assocs]
    rule_assocs_in_rulesets = [r for rs in effective_rulesets for r in rs.rule_assocs]

    def assoc_filter(assocs, to_remove):

        def _f(a):
            for rem in to_remove:
                if a.rule == rem.rule and a.invert == rem.invert and a.blocking == rem.blocking:
                    return False
            return True

        return [a for a in assocs if _f(a)]

    remaining_rule_assocs = assoc_filter(rule_assocs, rule_assocs_in_rulesets)
    if remaining_rule_assocs:
        msg = "node %r: RULES NOT IN A RULESET (INVALID!)" % (node, [r.to_dict() for r in remaining_rule_assocs])
        logg.warning(msg)
        raise ValueError(msg)
    special_ruleset = node.get_special_access_ruleset(ruletype)
    special_rule_assocs = special_ruleset.rule_assocs if special_ruleset else []
    return inherited_ruleset_assocs, own_ruleset_assocs, special_ruleset, special_rule_assocs


@dec_entry_log
def getContent(req, ids):

    hidden_edit_functions_for_current_user = current_user.hidden_edit_functions
    if 'acls' in hidden_edit_functions_for_current_user:
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if len(ids) != 1:  # should not happen
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/modules/acls.html", {}, macro="acl_editor_error")

    # check write access to node
    idstr = ids[0]
    nid = long(idstr)
    node = q(Node).get(nid)
    if not node.has_write_access():
        req.setStatus(httpstatus.HTTP_FORBIDDEN)
        return req.getTAL("web/edit/edit.html", {}, macro="access_error")

    if "save" in req.params:
        logg.info("%r change access %r", current_user, idstr)
        if req.params.get("type") == "acl":

            for rule_type in rule_types:

                ruleset_names_from_request = [rsn for rsn in req.params.get(u"left%s" % rule_type, u"").split(u";") if rsn.strip()]

                rules_info_dict = make_access_rules_info_dict(node, rule_type)
                rulesets_not_inherited = rules_info_dict.get('rulesets_not_inherited', [])

                ruleset_names_not_inherited = [rs_dict.get('ruleset_name') for rs_dict in rulesets_not_inherited]

                to_be_removed_rulesets = set(ruleset_names_not_inherited) - set(ruleset_names_from_request)
                to_be_added_rulesets = set(ruleset_names_from_request) - set(ruleset_names_not_inherited) - {'__special_rule__'}

                if to_be_removed_rulesets:
                    msg = "node %r: %r removing rulesets %r" % (node, rule_type, to_be_removed_rulesets)
                    logg.info(msg)
                    for ruleset_name in to_be_removed_rulesets:
                        node.access_ruleset_assocs.filter_by(ruleset_name=ruleset_name,
                                                             ruletype=rule_type).delete()

                if to_be_added_rulesets:
                    msg = "node %r: %r adding rulesets %r" % (node, rule_type, to_be_added_rulesets)
                    logg.info(msg)
                    for ruleset_name in to_be_added_rulesets:
                        node.access_ruleset_assocs.append(NodeToAccessRuleset(ruleset_name=ruleset_name, ruletype=rule_type))

            db.session.commit()

        if req.params.get("type") == "user":

            additional_rules = {}
            additional_rules_inherited = {}
            additional_rules_not_inherited = {}

            for rule_type in rule_types:

                user_ids_from_request = [rsn for rsn in req.params.get(u"leftuser%s" % rule_type, u"").split(u";") if rsn.strip()]

                rules_info_dict = make_access_rules_info_dict(node, rule_type)
                rulesets_not_inherited = rules_info_dict.get('rulesets_not_inherited', [])

                additional_rules[rule_type] = rules_info_dict.get('additional_rules', [])
                additional_rules_inherited[rule_type] = [rd for rd in additional_rules[rule_type] if rd.get('inherited', False)]
                additional_rules_not_inherited[rule_type] = [rd for rd in additional_rules[rule_type] if not rd.get('inherited', False)]

                uids = []
                for ar_dict in additional_rules_not_inherited[rule_type]:
                    ar_id = ar_dict.get('rule_id')
                    ar = q(AccessRule).get(ar_id)
                    test_result = decider_is_private_user_group_access_rule(ar)
                    if not type(test_result) == User:
                        continue
                    elif not test_result.id in user_ids_from_request:
                        assoc = node.access_rule_assocs.filter_by(rule_id=ar_id, ruletype=rule_type).scalar()
                        node.access_rule_assocs.remove(assoc)
                    else:
                        uids.append(test_result.id)

                for uid in user_ids_from_request:
                    if uid in uids:
                        continue
                    # add access rule
                    user = q(User).get(uid)
                    pug_id = user.private_group_id
                    ar = q(AccessRule).filter(AccessRule.group_ids.all(pug_id))\
                          .filter_by(subnets=None, dateranges=None,
                                     invert_group=False, invert_date=False, invert_subnet=False)\
                          .scalar()
                    if not ar:
                        ar = AccessRule(group_ids = [pug_id])
                    assoc = NodeToAccessRule(rule=ar, ruletype=rule_type, invert=False, blocking=False)
                    node.access_rule_assocs.append(assoc)

            db.session.commit()

    action = req.params.get("action", "")

    retacl = ""
    if not action:

        rulesetnamelist = [t[0] for t in q(AccessRuleset.name).order_by(AccessRuleset.name).all()]
        private_ruleset_names = [t[0] for t in q(NodeToAccessRuleset.ruleset_name).filter_by(private=True).all()]
        rulesetnamelist = [rulesetname for rulesetname in rulesetnamelist if not rulesetname in private_ruleset_names]

        for rule_type in rule_types:
            inherited_ruleset_assocs, \
            own_ruleset_assocs, \
            special_ruleset, special_rule_assocs = get_access_rules_info(node, rule_type)
            retacl += req.getTAL("web/edit/modules/acls.html",
                                 makeList(req,
                                          own_ruleset_assocs,  #not_inherited_ruleset_names[rule_type],  # rights
                                          inherited_ruleset_assocs,  #inherited_ruleset_names[rule_type],  # readonlyrights
                                          special_ruleset,  #additional_rules_inherited[rule_type],
                                          special_rule_assocs,  #additional_rules_not_inherited[rule_type],
                                          rulesetnamelist,
                                          private_ruleset_names,
                                          rule_type=rule_type),
                                 macro="edit_acls_selectbox")

    if action == 'get_userlist':  # load additional rights by ajax

        rulesetnamelist = [t[0] for t in q(AccessRuleset.name).order_by(AccessRuleset.name).all()]
        private_ruleset_names = [t[0] for t in q(NodeToAccessRuleset.ruleset_name).filter_by(private=True).all()]
        rulesetnamelist = [rulesetname for rulesetname in rulesetnamelist if not rulesetname in private_ruleset_names]

        retuser = ""
        for rule_type in rule_types:
            inherited_ruleset_assocs, \
            own_ruleset_assocs, \
            special_ruleset, special_rule_assocs = get_access_rules_info(node, rule_type)
            retuser += req.getTAL("web/edit/modules/acls.html",
                                  makeUserList(req,
                                               own_ruleset_assocs,  # not_inherited_ruleset_names[rule_type],  # rights
                                               inherited_ruleset_assocs,  # inherited_ruleset_names[rule_type],  # readonlyrights
                                               special_ruleset,  # additional_rules_inherited[rule_type],
                                               special_rule_assocs,  # additional_rules_not_inherited[rule_type],
                                               rulesetnamelist,
                                               private_ruleset_names,
                                               rule_type=rule_type),
                                  macro="edit_acls_userselectbox")
        req.write(retuser)
        return ""

    runsubmit = "\nfunction runsubmit(){\n"
    for rule_type in rule_types:
        runsubmit += "\tmark(document.myform.left" + rule_type + ");\n"
        runsubmit += "\tmark(document.myform.leftuser" + rule_type + ");\n"
    runsubmit += "\tdocument.myform.submit();\n}\n"

    return req.getTAL("web/edit/modules/acls.html",
                      {"runsubmit": runsubmit, "idstr": idstr, "contentacl": retacl,
                       "adminuser": current_user.is_admin},
                      macro="edit_acls")


