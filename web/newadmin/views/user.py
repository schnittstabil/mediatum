# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2016 by the mediaTUM authors
    :license: GPL3, see COPYING for details
"""
from __future__ import absolute_import
import logging
from core import db, User, UserGroup, AuthenticatorInfo
from markupsafe import Markup
from wtforms.fields.core import StringField
from web.newadmin.views import BaseAdminView
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField
from flask.ext.admin import form
from core.auth import INTERNAL_AUTHENTICATOR_KEY


logg = logging.getLogger(__name__)


def _link_format_node_id_column(node_id):
    # XXX: just for testing, this should link to this instance
    return Markup('<a href="https://mediatum.ub.tum.de/node?id={0}">{0}</a>'.format(node_id))

class UserView(BaseAdminView):

    column_exclude_list = ("created", "password_hash", "salt", "comment",
                           "private_group", "can_edit_shoppingbag", "can_change_password")
    column_filters = ("authenticator_info", "display_name", "login_name", "organisation")
    can_export = True

    column_details_list = ("home_dir", "authenticator_info", "id", "login_name", "display_name", "lastname",
                           "firstname", "telephone", "organisation", "comment", "email", "password_hash",
                           "salt", "last_login", "active", "can_edit_shoppingbag", "can_change_password",
                           "created_at", "group_names")
    """
    """

    column_labels = dict(group_names = 'Groups')

    column_formatters = {
        "home_dir": lambda v, c, m, p: _link_format_node_id_column(m.home_dir.id) if m.home_dir else None
    }
    column_searchable_list = ("display_name", "login_name", "organisation")
    column_editable_list = ("login_name", "email")
    form_excluded_columns = ("home_dir", "created", "password_hash", "salt",
                             "versions", "shoppingbags", "private_group", "group_assocs")

    form_overrides = {
        "email": StringField
    }

    form_extra_fields = {
        "groups": QuerySelectMultipleField(query_factory=lambda: db.query(UserGroup).order_by(UserGroup.name),
                                           widget=form.Select2Widget(multiple=True)),
        "password": StringField()
    }

    def __init__(self, session=None, *args, **kwargs):
        super(UserView, self).__init__(User, session, category="User", *args, **kwargs)

    def on_model_change(self, form, user, is_created):
        if form.password.data and user.authenticator_info.authenticator_key == INTERNAL_AUTHENTICATOR_KEY:
            user.change_password(form.password.data)


class UserGroupView(BaseAdminView):

    form_excluded_columns = "user_assocs"
    column_details_list = ["id", "name", "description", "hidden_edit_functions", "is_editor_group",
                           "is_workflow_editor_group", "is_admin_group", "created_at", "user_names"]

    column_labels = dict(user_names = 'Users')

    form_extra_fields = {
        "users": QuerySelectMultipleField(query_factory=lambda: db.query(User).order_by(User.login_name),
                                          widget=form.Select2Widget(multiple=True)),
    }


    def __init__(self, session=None, *args, **kwargs):
        super(UserGroupView, self).__init__(UserGroup, session, category="User", *args, **kwargs)


class AuthenticatorInfoView(BaseAdminView):

    def __init__(self, session=None, *args, **kwargs):
        super(AuthenticatorInfoView, self).__init__(AuthenticatorInfo, session, category="User", *args, **kwargs)
