# Copyright (C) July 2018:  TF TECH NV in Belgium see https://www.threefold.tech/
# In case TF TECH NV ceases to exist (e.g. because of bankruptcy)
#   then Incubaid NV also in Belgium will get the Copyright & Authorship for all changes made since July 2018
#   and the license will automatically become Apache v2 for all code related to Jumpscale & DigitalMe
# This file is part of jumpscale at <https://github.com/threefoldtech>.
# jumpscale is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# jumpscale is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License v3 for more details.
#
# You should have received a copy of the GNU General Public License
# along with jumpscale or jumpscale derived works.  If not, see <http://www.gnu.org/licenses/>.
# LICENSE END


from Jumpscale import j

from .BCDB import BCDB
from .BCDBModel import BCDBModel

import os
import sys
import redis
import copy
import copy


class BCDBFactory(j.application.JSBaseFactoryClass):

    __jslocation__ = "j.data.bcdb"

    def _init(self, **kwargs):

        self._log_debug("bcdb starts")
        self._bcdb_instances = {}  # key is the name
        self._path = j.sal.fs.getDirName(os.path.abspath(__file__))

        self._code_generation_dir_ = None

        j.clients.redis.core_get()  # just to make sure the redis got started

        self._BCDBModelClass = BCDBModel  # j.data.bcdb._BCDBModelClass

        # will make sure the toml schema's are loaded
        j.data.schema.add_from_path("%s/models_system" % self._dirpath)

        self._load()

    def _load(self):

        self._config_data_path = j.core.tools.text_replace("{DIR_CFG}/bcdb_config")
        if j.sal.fs.exists(self._config_data_path):
            data_encrypted = j.sal.fs.readFile(self._config_data_path, binary=True)
            try:
                data = j.data.nacl.default.decryptSymmetric(data_encrypted)
            except Exception as e:
                if str(e).find("Ciphertext failed") != -1:
                    raise j.exceptions.Base("%s cannot be decrypted with secret" % self._config_data_path)
                raise e
            self._config = j.data.serializers.msgpack.loads(data)
        else:
            self._config = {}

        self._system = None

    def get_system(self, reset=False):
        """
        sqlite based BCDB, don't need ZDB for this
        :return:
        """

        if not self._system:
            # storclient = j.clients.sqlitedb.client_get(name="system")
            storclient = j.clients.rdb.client_get(name="system")
            self._system = self.get("system", storclient=storclient, reset=reset)
        return self._system

    def get_test(self, reset=False):
        bcdb = j.data.bcdb.new(name="testbcdb")
        bcdb2 = j.data.bcdb._bcdb_instances["testbcdb"]
        assert bcdb2.storclient == None
        return bcdb

    @property
    def _BCDBModelClass(self):
        return BCDBModel

    @property
    def WebDavProvider(self):
        from .connectors.webdav.BCDBResourceProvider import BCDBResourceProvider

        return BCDBResourceProvider()

    @property
    def instances(self):
        res = []
        config = self._config.copy()
        for name, data in config.items():
            self._log_debug(data)
            bcdb = self.get(name)
            res.append(bcdb)
        return res

    def index_rebuild(self):
        """
        kosmos 'j.data.bcdb.index_rebuild()'
        :return:
        """
        for bcdb in self.instances:
            bcdb.index_rebuild()

    def check(self):
        """
        not implemented yet, will check the indexes & data
        :return:
        """
        # TODO:
        pass

    def reset(self):
        """
        will remove all remembered connections
        :return:
        """
        j.sal.fs.remove(self._config_data_path)
        self._config = {}
        self._bcdb_instances = {}

    def destroy_all(self):
        """
        destroy all remembered BCDB's
        SUPER DANGEROUS
        all data will be lost
        :return:
        """
        names = [name for name in self._config.keys()]
        j.servers.tmux.window_kill("sonic")
        self._bcdb_instances = {}
        storclients = []
        for name in names:
            try:
                cl = self._get_storclient(name)
            except:
                self._log_warning("cannot connect storclient:%s" % name)
                continue
            if cl not in storclients:
                storclients.append(cl)
        for cl in storclients:
            if cl.type == "SDB":
                cl.sqlitedb.close()
            cl.flush()
        for key in j.core.db.keys("bcdb:*"):
            j.core.db.delete(key)
        j.sal.fs.remove(j.core.tools.text_replace("{DIR_VAR}/bcdb"))
        j.sal.fs.remove(self._config_data_path)
        self._load()
        assert self._config == {}

    def exists(self, name):
        if name in self._bcdb_instances:
            if not name in self._config:
                j.shell()
            assert name in self._config
            return True

        return name in self._config

    def destroy(self, name):
        assert name
        assert isinstance(name, str)

        if name in self._config:
            storclient = self._get_storclient(name)
        else:
            raise RuntimeError("there should always be a storclient")

        dontuse = BCDB(storclient=storclient, name=name, reset=True)

        if name in self._bcdb_instances:
            self._bcdb_instances.pop(name)

        if name in self._config:
            self._config.pop(name)
            self._config_write()

    def get(self, name, storclient=None, reset=False, fromcache=True):
        """
        will create a new one or an existing one if it exists
        :param name:
        :param reset: will remove the data
        :param storclient: optional
            e.g. j.clients.rdb.client_get()  (would be the core redis
            e.g. j.clients.zdb.client_get() would be a zdb client
        :return:
        """
        if not fromcache:
            if name in self._bcdb_instances:
                self._bcdb_instances.pop(name)
        if self.exists(name):
            return self._get(name=name, reset=reset, storclient=storclient)
        else:
            return self.new(name=name, storclient=storclient, reset=reset)

    def _get_vfs(self):
        from .BCDBVFS import BCDBVFS

        return BCDBVFS(self._bcdb_instances)

    def _get_storclient(self, name):
        data = copy.copy(self._config[name])

        if data["type"] == "zdb":
            if "admin" in data:
                if data["admin"]:
                    raise j.exceptions.Base("can only use ZDB connection which is not admin")
                data.pop("admin")
            if "type" in data:
                data.pop("type")
            storclient = j.clients.zdb.client_get(**data)
        elif data["type"] == "rdb":
            if "type" in data:
                data.pop("type")
            storclient = j.clients.rdb.client_get(**data)
        elif data["type"] == "sdb":
            if "type" in data:
                data.pop("type")
            storclient = j.clients.sqlitedb.client_get(**data)
        else:
            raise j.exceptions.Input("type storclient not found:%s" % data["type"])
        return storclient

    def _get(self, name, storclient=None, reset=False):
        """[summary]
        get instance of bcdb
        :param name:
        :param storclient: can add this if bcdb instance doesn't exist
        :return:
        """
        # DO NOT CHANGE if_not_exist_die NEED TO BE TRUE
        data = {}
        if name in self._bcdb_instances:
            bcdb = self._bcdb_instances[name]
            assert name in self._config
            return bcdb
        elif name in self._config:
            if not storclient:
                storclient = self._get_storclient(name)
        else:
            raise j.exceptions.Base("did not find bcdb with name:%s" % name)

        if reset:
            # its the only 100% safe way to get all out for now
            dontuse = BCDB(storclient=storclient, name=name, reset=reset)
        self._bcdb_instances[name] = BCDB(storclient=storclient, name=name)
        return self._bcdb_instances[name]

    def _config_write(self):
        data = j.data.serializers.msgpack.dumps(self._config)
        data_encrypted = j.data.nacl.default.encryptSymmetric(data)
        j.sal.fs.writeFile(self._config_data_path, data_encrypted)

    def new(self, name, storclient=None, reset=False):
        """
        create a new instance
        :param name:
        :param storclient: optional
            e.g. j.clients.rdb.client_get()  (would be the core redis
            e.g. j.clients.zdb.client_get() would be a zdb client
            e.g. j.clients.sqlitedb.client_get() would be a sqlite client

            if not specified then will be storclient = j.clients.sqlitedb.client_get(nsname="system")

        :return:
        """

        self._log_info("new bcdb:%s" % name)
        if self.exists(name=name):
            if not reset:
                raise j.exceptions.Input("cannot create new bcdb '%s' already exists, and reset not used" % name)
            else:
                self.destroy(name=name)

        if not storclient:
            storclient = j.clients.sqlitedb.client_get(name=name)
        else:
            if j.data.types.string.check(storclient):
                raise j.exceptions.Base("storclient cannot be str")
        data = {}

        assert isinstance(storclient.type, str)
        if storclient.type == "SDB":
            data["name"] = storclient.nsname
            data["type"] = "sdb"
            # link to which redis to connect to (name of the redis client in JSX)
        elif storclient.type == "RDB":
            data["name"] = storclient.nsname
            data["type"] = "rdb"
            data["redisconfig_name"] = storclient._redis.redisconfig_name
            # link to which redis to connect to (name of the redis client in JSX)

        else:
            data["name"] = storclient.nsname
            data["admin"] = storclient.admin
            data["addr"] = storclient.addr
            data["port"] = storclient.port
            data["mode"] = str(storclient.mode)
            data["secret"] = storclient.secret_
            data["type"] = "zdb"

        assert data["name"]

        self._config[name] = data
        self._config_write()
        self._load()

        bcdb = self._get(name=name, reset=False, storclient=storclient)

        assert bcdb.storclient
        assert bcdb.storclient.type == storclient.type

        assert bcdb.name in self._config

        return bcdb

    @property
    def _code_generation_dir(self):
        if not self._code_generation_dir_:
            path = j.sal.fs.joinPaths(j.dirs.VARDIR, "codegen", "models")
            j.sal.fs.createDir(path)
            if path not in sys.path:
                sys.path.append(path)
            j.sal.fs.touch(j.sal.fs.joinPaths(path, "__init__.py"))
            self._log_debug("codegendir:%s" % path)
            self._code_generation_dir_ = path
        return self._code_generation_dir_

    def _load_test_model(self, type="zdb", schema=None, datagen=False):
        """

        kosmos 'j.data.bcdb._load_test_model(type="zdb",datagen=True)'
        kosmos 'j.data.bcdb._load_test_model(type="sqlite",datagen=True)'
        kosmos 'j.data.bcdb._load_test_model(type="rdb",datagen=True)'

        :param reset:
        :param type:
        :param schema:
        :return:
        """

        if not schema:
            schema = """
            @url = despiegk.test
            llist2 = "" (LS)
            name** = ""
            email** = ""
            nr** = 0
            date_start** = 0 (D)
            description = ""
            token_price** = "10 USD" (N)
            hw_cost = 0.0 #this is a comment
            llist = []
            llist3 = "1,2,3" (LF)
            llist4 = "1,2,3" (L)
            llist5 = "1,2,3" (LI)
            U = 0.0
            pool_type = "managed,unmanaged" (E)
            """

        type = type.lower()

        def startZDB():
            zdb = j.servers.zdb.test_instance_start()
            storclient_admin = zdb.client_admin_get()
            assert storclient_admin.ping()
            secret = "1234"
            storclient = storclient_admin.namespace_new("test", secret=secret)
            return storclient

        if type == "rdb":
            storclient = startZDB()
            storclient = j.clients.rdb.client_get()  # will be to core redis
            bcdb = j.data.bcdb.new(name="test", storclient=storclient, reset=True)
        elif type == "sqlite":
            bcdb = j.data.bcdb.new(name="test", reset=True)
        elif type == "zdb":
            storclient = startZDB()
            storclient.flush()
            assert storclient.nsinfo["public"] == "no"
            assert storclient.ping()
            bcdb = j.data.bcdb.new(name="test", storclient=storclient, reset=True)
        else:
            raise j.exceptions.Base("only rdb,zdb,sqlite for stor")

        assert bcdb.name == "test"

        bcdb.reset()  # empty

        assert bcdb.name == "test"

        schemaobj = j.data.schema.get_from_text(schema)
        model = bcdb.model_get(schema=schemaobj)

        self._log_debug("bcdb already exists")

        if type.lower() in ["zdb"]:
            # print(model.storclient.nsinfo["entries"])
            assert model.storclient.nsinfo["entries"] == 1
        else:
            assert len(model.find()) == 0

        if datagen:
            for i in range(3):
                model_obj = model.new()
                model_obj.llist.append(1)
                model_obj.llist2.append("yes")
                model_obj.llist2.append("no")
                model_obj.llist3.append(1.2)
                model_obj.date_start = j.data.time.epoch
                model_obj.U = 1.1
                model_obj.nr = i
                model_obj.token_price = "10 EUR"
                model_obj.description = "something"
                model_obj.name = "name%s" % i
                model_obj.email = "info%s@something.com" % i
                model_obj2 = model.set(model_obj)
            assert len(model.find()) == 3

        return bcdb, model

    def _instance_names(self, prefix=None):
        items = []
        # items = [key for key in self.__dict__.keys() if not key.startswith("_")]
        for bcdb in self.instances:
            items.append(bcdb.name)
        items.sort()
        # print(items)
        return items

    def __setattr__(self, key, value):
        if key in ["system", "test"]:
            raise j.exceptions.Base("no system or test allowed")
        self.__dict__[key] = value

    def __str__(self):

        out = "## {GRAY}BCDBS: {BLUE}\n\n"

        for bcdb in self.instances:
            out += " = %s" % bcdb.name

        out += "{RESET}"
        out = j.core.tools.text_replace(out)
        print(out)
        # TODO: *1 dirty hack, the ansi codes are not printed, need to check why
        return ""

    __repr__ = __str__

    def test(self, name=""):
        """
        following will run all tests

        kosmos 'j.data.bcdb.test()'


        """

        self._test_run(name=name)

        self._log_info("All TESTS DONE")
        return "OK"
