from Jumpscale import j
from .ZDBServer import ZDBServer

JSConfigs = j.application.JSBaseConfigsClass


class ZDBServers(JSConfigs):
    """
    Open Publish factory
    """

    __jslocation__ = "j.servers.zdb"
    _CHILDCLASS = ZDBServer

    def _init(self, **kwargs):
        self._default = None

    @property
    def default(self):
        if not self._default:
            self._default = self.new(name="default")
        return self._default

    def build(self, reset=True):
        """
        kosmos 'j.servers.zdb.build()'
        """
        j.builders.db.zdb.install(reset=reset)

    def test_instance_start(
        self, destroydata=False, namespaces=[], admin_secret="123456", namespaces_secret="1234", restart=False
    ):
        """

        kosmos 'j.servers.zdb.test_instance_start(reset=True)'

        start a test instance with self.adminsecret 123456
        will use port 9901
        and name = test

        production is using other ports and other secret

        :return:
        """
        zdb = self.get(name="test", port=9901)

        if destroydata:
            zdb.destroy()
            j.clients.redis._cache_clear()  # make sure all redis connections gone

        zdb.start()
        zdb.save()

        cla = zdb.client_admin_get()

        for ns in namespaces:
            if not cla.namespace_exists(ns):
                cla.namespace_new(ns, secret=namespaces_secret)
            else:
                if destroydata:
                    cla.namespace_delete(ns)
                    cla.namespace_new(ns, secret=namespaces_secret)

        if destroydata:
            j.clients.redis._cache_clear()  # make sure all redis connections gone

        return zdb

    def test_instance_stop(self, destroy=True):
        zdb = self.get(name="test", port=9901)
        zdb.stop()
        if destroy:
            zdb.destroy()
            zdb.delete()

    def test(self, build=False):
        """
        kosmos 'j.servers.zdb.test(build=True)'
        kosmos 'j.servers.zdb.test()'
        """

        if build:
            self.build()
        zdb = self.test_instance_start(namespaces=["test"], restart=True, destroydata=True)

        cl = zdb.client_get(nsname="test")

        assert cl.ping()

        self.test_instance_stop()

        print("TEST OK")
