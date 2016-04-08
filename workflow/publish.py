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
from .workflow import WorkflowStep, registerStep
from core import db
from core.database.postgres.permission import AccessRule, AccessRulesetToRule
from core import UserGroup
q = db.query


def register():
    #tree.registerNodeClass("workflowstep-publish", WorkflowStep_Publish)
    registerStep("workflowstep_publish")


class WorkflowStep_Publish(WorkflowStep):

    def runAction(self, node, op=""):
        ugid = q(UserGroup).filter_by(name=u'Workflow').one().id

        # remove access rule with 'Workflow' user group id
        special_access_ruleset = node.get_special_access_ruleset(ruletype=u'read')
        for e in special_access_ruleset.rule_assocs:
            ar = q(AccessRule).get(e.rule_id)
            if ar is not None and ar.group_ids is not None and (ugid in ar.group_ids):
                q(AccessRulesetToRule).filter_by(rule_id=ar.id).delete()
                q(AccessRule).filter_by(id=e.rule_id).delete()
        db.session.commit()

        self.forward(node, True)
