class MtQuery(Query):


    def prefetch_attrs(self):
        from core import Node
        return self.options(undefer(Node.attrs))

    def _find_nodeclass(self):
        from core import Node
        """Returns the query's underlying model classes."""
        return [
            d['entity']
            for d in self.column_descriptions
            if issubclass(d['entity'], Node)
        ]

    def filter_read_access(self, user=None, ip=None, req=None):
        return self._filter_access("read", user, ip, req)

    def filter_write_access(self, user=None, ip=None, req=None):
        return self._filter_access("write", user, ip, req)

    def filter_data_access(self, user=None, ip=None, req=None):
        return self._filter_access("data", user, ip, req)

    def _filter_access(self, accesstype, user=None, ip=None, req=None):
        from core.users import get_guest_user

        if user is None and ip is None:
            if req is None:
                req = request

            from core.users import user_from_session
            user = user_from_session(req.session)

            # XXX: like in mysql version, what's the real solution?
            if "," in req.remote_addr:
                logg.warn("multiple IP adresses %s, refusing IP-based access", req.remote_addr)
                ip = None
            else:
                ip = IPv4Address(req.remote_addr)

        if user is None:
            user = get_guest_user()

        # admin sees everything ;)
        if user.is_admin:
            return self

        if ip is None:
            ip = IPv4Address("0.0.0.0")

        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return self
        else:
            nodeclass = nodeclass[0]

        db_funcs = {
            "read": mediatumfunc.has_read_access_to_node,
            "write": mediatumfunc.has_write_access_to_node,
            "data": mediatumfunc.has_data_access_to_node
        }

        try:
            db_accessfunc = db_funcs[accesstype]
        except KeyError:
            raise ValueError("accesstype '{}' does not exist, accesstype must be one of: read, write, data".format(accesstype))

        read_access = db_accessfunc(nodeclass.id, user.group_ids, ip, sqlfunc.current_date())
        return self.filter(read_access)

    def get(self, ident):
        nodeclass = self._find_nodeclass()
        if not nodeclass:
            return Query.get(self, ident)
        else:
            nodeclass = nodeclass[0]
        active_version = Query.get(self, ident)
        Transaction = versioning_manager.transaction_cls
        if active_version is None:
            ver_cls = version_class(nodeclass)
            return (self.session.query(ver_cls).join(Transaction, ver_cls.transaction_id == Transaction.id)
                    .join(Transaction.meta_relation)
                    .filter_by(key=u'alias_id', value=unicode(ident)).scalar())

        return active_version
