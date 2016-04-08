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
from core.database.postgres.permission import AccessRuleset
from core import db

q = db.query


def makeList(req, name, not_inherited_ruleset_names, inherited_ruleset_names, additional_rules_inherited=[], additional_rules_not_inherited=[], overload=0, type=""):
    rightsmap = {}
    rorightsmap = {}

    rulelist = q(AccessRuleset).order_by(AccessRuleset.name).all()

    val_left = []
    val_right = []

    # inherited rules
    for rule_name in inherited_ruleset_names:
        if rule_name not in rorightsmap:
            val_left.append("""<optgroup label="%s"></optgroup>""" % rule_name)
            rorightsmap[rule_name] = 1

    for r in additional_rules_inherited:
        val_left.append("""<optgroup label="%s"></optgroup>""" % (translate("edit_acl_special_rule", lang(req))))

    # node level rules
    for rule_name in not_inherited_ruleset_names:
        if rule_name in rorightsmap and not overload:
            continue
        val_left.append("""<option value="%s">%s</option>""" % (rule_name, rule_name))
        rightsmap[rule_name] = 1

    for r in additional_rules_not_inherited:
        val_left.append("""<option value="__special_rule__">%s</option>""" % (translate("edit_acl_special_rule", lang(req)), ))

    for rule in rulelist:
        rule_name = rule.name
        if rule_name not in rightsmap and rule_name not in rorightsmap:
            val_right.append("""<option value="%s">%s</option>""" % (rule_name, rule_name))

    res = {"name": name, "val_left": "".join(val_left), "val_right": "".join(val_right), "type": type}

    return res
