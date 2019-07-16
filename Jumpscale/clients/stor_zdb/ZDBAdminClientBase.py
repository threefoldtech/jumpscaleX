from Jumpscale import j


class ZDBAdminClientBase:
    def namespace_exists(self, name):
        assert self.admin
        try:
            self.redis.execute_command("NSINFO", name)
            # self._log_debug("namespace_exists:%s" % name)
            return True
        except Exception as e:
            if not "Namespace not found" in str(e):
                raise RuntimeError("could not check namespace:%s, error:%s" % (name, e))
            # self._log_debug("namespace_NOTexists:%s" % name)
            return False

    def namespaces_list(self):
        assert self.admin
        res = self.redis.execute_command("NSLIST")
        return [i.decode() for i in res]

    def namespace_new(self, name, secret=None, maxsize=0, die=False):
        """
        check namespace exists & will return zdb client to that namespace

        :param name:
        :param secret:
        :param maxsize:
        :param die:
        :return:
        """
        assert self.admin
        self._log_debug("namespace_new:%s" % name)
        if not self.namespace_exists(name):
            self._log_debug("namespace does not exists")
            self.redis.execute_command("NSNEW", name)
        else:
            if die:
                raise RuntimeError("namespace already exists:%s" % name)

        if secret:
            self._log_debug("set secret")
            self.redis.execute_command("NSSET", name, "password", secret)
            self.redis.execute_command("NSSET", name, "public", "no")

        if maxsize is not 0:
            self._log_debug("set maxsize")
            self.redis.execute_command("NSSET", name, "maxsize", maxsize)

        self._log_debug("connect client")

        ns = j.clients.zdb.client_get(addr=self.addr, port=self.port, mode=self.mode, secret=secret, nsname=name)

        assert ns.ping()
        if secret:
            assert ns.nsinfo["public"] == "no"
        else:
            assert ns.nsinfo["public"] == "yes"

        return ns

    def namespace_get(self, name, secret=""):
        assert self.admin
        return self.namespace_new(name, secret)

    def namespace_delete(self, name):
        assert self.admin
        if self.namespace_exists(name):
            self._log_debug("namespace_delete:%s" % name)
            self.redis.execute_command("NSDEL", name)

    def reset(self, ignore=[]):
        """
        dangerous, will remove all namespaces & all data
        :param: list of namespace names not to reset
        :return:
        """
        assert self.admin
        for name in self.namespaces_list():
            if name not in ["default"] and name not in ignore:
                self.namespace_delete(name)