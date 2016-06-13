#Copyright (c) 2012, Konsta Vesterinen

#All rights reserved.

#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#
#* Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#* Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#* The names of the contributors may not be used to endorse or promote products
#  derived from this software without specific prior written permission.

#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
#INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
#BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
#OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# modifications by Tobias Stenzel <tobias.stenzel@tum.de>

"""
AthanaPlugin offers way of integrating Athana with
SQLAlchemy-Continuum. AthanaPlugin adds two columns for Transaction model,
namely `user_id` and `remote_addr`.

These columns are automatically populated when transaction object is created.
The `remote_addr` column is populated with the value of the remote address that
made current request. The `user_id` column is populated with the id of the
current_user object.

::

    from core.transition.continuum_athanaplugin import AthanaPlugin
    from sqlalchemy_continuum import make_versioned


    make_versioned(plugins=[AthanaPlugin()])
    
    
    Most of the code was taken from sqlalchemy_continuum's `FlaskPlugin`
"""
from __future__ import absolute_import

from core import app
from core.transition.globals import request
from core.transition.globals import _app_ctx_stack, _request_ctx_stack

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_continuum.plugins.base import Plugin


def fetch_current_user_id():
    from core.transition.globals import current_user

    # Return None if we are outside of request context.
    if _app_ctx_stack.top is None or _request_ctx_stack.top is None:
        return
    try:
        return current_user.id
    except (AttributeError, NoResultFound):
        return


def fetch_remote_addr():
    # Return None if we are outside of request context.
    if _app_ctx_stack.top is None or _request_ctx_stack.top is None:
        return
    return request.remote_addr


class AthanaPlugin(Plugin):
    def __init__(
        self,
        current_user_id_factory=None,
        remote_addr_factory=None
    ):
        self.current_user_id_factory = (
            fetch_current_user_id if current_user_id_factory is None
            else current_user_id_factory
        )
        self.remote_addr_factory = (
            fetch_remote_addr if remote_addr_factory is None
            else remote_addr_factory
        )

    def transaction_args(self, uow, session):
        return {
            'user_id': self.current_user_id_factory(),
            'remote_addr': self.remote_addr_factory()
        }