from Jumpscale import j
from Jumpscale.sal.bash.Profile import Profile

builder_method = j.builders.system.builder_method


class BuilderLua(j.builders.system._BaseClass):
    """
    needs openresty and openssl
    """

    NAME = "lua"

    def _init(self):
        self.ROCKS_PATHS_PROFILE = self._replace("{DIR_BUILD}/rocks_paths")

    @builder_method()
    def build(self, reset=False, deps_reset=False):
        """
        kosmos 'j.builders.runtimes.lua.build(reset=True)'
        :param install:
        :return:
        """
        if j.core.platformtype.myplatform.platform_is_ubuntu:
            j.builders.system.package.install(
                ["libsqlite3-dev", "libpcre3-dev", "libssl-dev", "perl", "make", "build-essential"]
            )

        j.builders.web.openresty.install(reset=deps_reset)
        # j.builders.libs.openssl.build(reset=deps_reset)  #DOES NOT WORK FOR NOW, maybe wrong version of openssl?

        url = "https://luarocks.org/releases/luarocks-3.1.3.tar.gz"
        dest = self._replace("{DIR_BUILD}/luarocks")
        self.tools.dir_ensure(dest)
        self.tools.file_download(
            url, to=dest, overwrite=False, retry=3, expand=True, minsizekb=100, removeTopDir=True, deletedest=True
        )
        C = """
        cd {DIR_BUILD}/luarocks
        ./configure --prefix=/sandbox/openresty/luarocks --with-lua=/sandbox/openresty/luajit
        make build
        make install

        cp {DIR_BUILD}/luarocks/luarocks /sandbox/bin/luarocks
        luarocks path > {ROCKS_PATHS_PROFILE}
        """

        # set showout to False to avoid text_replace of output log
        self._execute(C, showout=True)

    def profile_installer_select(self):

        def _clean_env(env_paths):
            build_lua_path = self._replace('{DIR_BUILD}/luarocks/')
            clean_path = ';'.join([path for path in env_paths.split(';') if not(
                path.startswith(build_lua_path) or path.startswith('/root'))])
            return clean_path

        if not j.sal.fs.exists(self.ROCKS_PATHS_PROFILE):
            self.build(reset=True)
            assert j.sal.fs.exists(self.ROCKS_PATHS_PROFILE)

        if not j.sal.fs.exists("/sandbox/openresty/luajit/include"):
            # we need the include headers so if not there need to build openresty
            j.builders.web.openresty.build(reset=True)

        # add lua_path and lua_cpath so lua libs/clibs can found by lua interpreter)
        luarocks_profile = Profile(self._bash, self.ROCKS_PATHS_PROFILE)

        lua_path = luarocks_profile.env_get("LUA_PATH")
        lua_path = _clean_env(lua_path)

        lua_cpath = luarocks_profile.env_get("LUA_CPATH")
        lua_cpath = _clean_env(lua_cpath)

        self.profile.env_set("LUA_PATH", lua_path)
        self.profile.env_set("LUA_CPATH", lua_cpath)
        self.profile.env_set("LUA_INCDIR", "/sandbox/openresty/luajit/include/luajit-2.1")
        # self.profile.env_set("LUA_INCDIR", "/sandbox/openresty/luajit/include")
        self.profile.path_add("/sandbox/bin")

        path = luarocks_profile.env_get("PATH").replace(";", ":")
        self.profile.path_add(path, check_exists=False)

    def lua_rock_install(self, name, reset=False):
        self._log_info("lua_rock_install: %s" % name)
        if not reset and self._done_check("lua_rock_install_%s" % name):
            return

        if j.core.platformtype.myplatform.platform_is_osx:
            C = "luarocks install $NAME CRYPTO_DIR=$CRYPTODIR OPENSSL_DIR=$CRYPTODIR "
            C = C.replace("$CRYPTODIR", "/usr/local/opt/openssl")
        else:
            # C = "luarocks install $NAME CRYPTO_DIR=$CRYPTODIR OPENSSL_DIR=$CRYPTODIR"
            # C = "luarocks install lapis CRYPTO_DIR=/sandbox OPENSSL_DIR=/sandbox"
            C = "luarocks install $NAME "
            C = C.replace("$CRYPTODIR", "/sandbox")
        C = C.replace("$NAME", name)
        # example crypto dir: /usr/local/openresty/openssl/

        self._execute(C)

        self._done_set("lua_rock_install_%s" % name)

    @builder_method()
    def lua_rocks_install(self, reset=True):
        """
        kosmos 'j.builders.runtimes.lua.lua_rocks_install()'
        :param install:
        :return:
        """
        self.profile_installer_select()

        # if j.core.platformtype.myplatform.platform_is_ubuntu:
        #     # j.builders.system.package.mdupdate()
        #     j.builders.system.package.ensure("geoip-database,libgeoip-dev")

        C = """
        luaossl
        # luasec
        lapis
        moonscript
        lapis-console
        LuaFileSystem
        # luasocket
        lua-cjson
        # lua-term
        # penlight
        # lpeg
        # mediator_lua

        # inspect

        lua-resty-redis-connector
        # lua-resty-openidc

        # LuaRestyRedis

        # lua-capnproto
        lua-toml

        # lua-resty-exec

        # lua-resty-influx
        lua-resty-repl
        lua-resty-auto-ssl
        #
        # lua-resty-iputils
        #
        # lsqlite3
        #
        # bcrypt
        # md5

        # date
        # uuid
        # lua-resty-cookie
        # lua-path

        # luazen

        # alt-getopt
        # lua-messagepack

        # lua-resty-qless
        # lua-geoip
        # luajwt
        # mooncrafts

        """

        for line in C.split("\n"):
            line = line.strip()
            if line == "":
                continue
            if line.startswith("#"):
                continue
            self.lua_rock_install(line, reset=reset)

        if j.core.platformtype.myplatform.platform_is_ubuntu:
            self.lua_rock_install("lua-geoip", reset=reset)
            self.lua_rock_install("lua-resty-jwt", reset=reset)
            self.lua_rock_install("lua-resty-iyo-auth", reset=reset)  # need to check how to get this to work on OSX

        cmd = self._replace(
            "rsync -rav  /sandbox/openresty/luarocks/lua_modules/lib/lua/5.1/ /sandbox/openresty/lualib"
        )
        self.tools.execute(cmd, die=False)
        cmd = self._replace(
            "rsync -rav /sandbox/openresty/luarocks/share/lua/5.1/luarocks/  /sandbox/openresty/lualib/"
        )
        self.tools.execute(cmd, die=False)

    # def build_crypto(self):
    #
    #     """
    #     # https://github.com/evanlabs/luacrypto
    #
    #     export OPENSSL_CFLAGS=-I/usr/local/opt/openssl/include/
    #     export OPENSSL_LIBS="-L/usr/local/opt/openssl/lib -lssl -lcrypto"
    #     export LUAJIT_LIB="/sandbox/openresty/luajit/lib"
    #     export LUAJIT_INC="/sandbox/openresty/luajit/include/luajit-2.1"
    #     export LUA_CFLAGS="-I/sandbox/openresty/luajit/include/luajit-2.1/"
    #     export LUA_LIB="/sandbox/openresty/luajit/lib"
    #     export LUA_INC="/sandbox/openresty/luajit/include/luajit-2.1"
    #
    #     :return:
    #     """

    @builder_method()
    def clean(self):
        """
        kosmos 'j.builders.runtimes.lua.cleanup()'
        :param install:
        :return:
        """

        C = """

        set -ex

        rm -rf /sandbox/openresty/luajit/lib/lua
        rm -rf /sandbox/openresty/luajit/lib/luarocks
        rm -rf /sandbox/openresty/luajit/lib/pkgconfig
        rm -rf /sandbox/openresty/pod
        rm -rf /sandbox/openresty/luarocks
        rm -rf /sandbox/openresty/luajit/include
        rm -rf /sandbox/openresty/luajit/lib/lua
        rm -rf /sandbox/openresty/luajit/lib/pkgconfig
        rm -rf /sandbox/openresty/luajit/share
        rm -rf /sandbox/var/build
        rm -rf /sandbox/root
        mkdir -p /sandbox/root

        """
        self._execute(C)

    @builder_method()
    def install(self, reset=False, deps_reset=False):
        """
        will build & install in sandbox
        kosmos 'j.builders.runtimes.lua.install()'
        :return:
        """
        self.lua_rocks_install(reset=deps_reset)

        # copy some binaries
        C = """

        set -e
        pushd /sandbox/openresty/luarocks/lib/luarocks/rocks-5.1/lapis/1.7.0-1/bin/
        cp lapis /sandbox/bin/lapis
        popd
        pushd '/sandbox/openresty/luarocks/lib/luarocks/rocks-5.1/moonscript/0.5.0-1/bin'
        cp moon /sandbox/bin/moon
        cp moonc /sandbox/bin/moonc
        popd


        """
        self._execute(C)

        # src = "/sandbox/code/github/threefoldtech/digitalmeX/sandbox/bin"
        # self.tools.copyTree(src, "/sandbox/bin/", rsyncdelete=False, recursive=False, overwriteFiles=True)

    @builder_method()
    def sandbox(self, reset=False, zhub_client=None):
        """Copy built bins to dest_path and create flist if create_flist = True

        :param dest_path: destination path to copy files into
        :type dest_path: str
        :param sandbox_dir: path to sandbox
        :type sandbox_dir: str
        :param create_flist: create flist after copying files
        :type create_flist:bool
        :param zhub_client: hub instance to upload flist tos
        :type zhub_client:str
        """
        dest_path = self.DIR_SANDBOX
        j.builders.web.openresty.sandbox(reset=reset)

        bins = ["lua", "_lapis.lua", "_moonc.lua", "_moon.lua", "_moonrocks.lua"]
        for bin_name in bins:
            dir_src = self.tools.joinpaths(j.core.dirs.BINDIR, bin_name)
            dir_dest = self.tools.joinpaths(dest_path, j.core.dirs.BINDIR[1:])
            self.tools.dir_ensure(dir_dest)
            self._copy(dir_src, dir_dest)

        lib_dest = self.tools.joinpaths(dest_path, "sandbox/lib")
        self.tools.dir_ensure(lib_dest)
        for bin in bins:
            dir_src = self.tools.joinpaths(j.core.dirs.BINDIR, bin)
            j.tools.sandboxer.libs_sandbox(dir_src, lib_dest, exclude_sys_libs=False)

    def copy_to_github(self):
        """
        kosmos 'j.builders.runtimes.lua.copy_to_github()'
        :return:
        """
        # assert self.executor.type=="local"
        path = "/sandbox/openresty/lualib"

        if j.core.platformtype.myplatform.platform_is_ubuntu:
            destbin = "%s/base/openresty/lualib" % j.clients.git.getContentPathFromURLorPath(
                "git@github.com:threefoldtech/sandbox_ubuntu.git"
            )
        elif j.core.platformtype.myplatform.platform_is_osx:
            destbin = "%s/base/openresty/lualib" % j.clients.git.getContentPathFromURLorPath(
                "git@github.com:threefoldtech/sandbox_osx.git"
            )
        else:
            raise RuntimeError("only ubuntu & osx support")

        dest = "%s/base/openresty/lualib" % j.clients.git.getContentPathFromURLorPath(
            "git@github.com:threefoldtech/sandbox_base.git"
        )

        for item in j.sal.fs.listFilesInDir(path, recursive=True):
            rdest = j.sal.fs.pathRemoveDirPart(item, path)
            if j.sal.fs.getFileExtension(item) == "so":
                d2 = destbin
            elif j.sal.fs.getFileExtension(item) == "lua":
                d2 = dest
            else:
                raise RuntimeError(item)
            dir_dest_full = j.sal.fs.getDirName(self.tools.joinpaths(d2, rdest))
            self.tools.dir_ensure(dir_dest_full)
            dest_full = self.tools.joinpaths(d2, rdest)
            self._copy(item, dest_full)

        self.clean()

    def clean(self):
        C = """
        rm -rf {DIR_BUILD}
        rm -rf /tmp/luarocks*
        """
        self._execute(C)

    @property
    def startup_cmds(self):
        cmd = """
        rm -rf {DIR_TEMP}/lapis_test
        mkdir -p {DIR_TEMP}/lapis_test
        cd {DIR_TEMP}/lapis_test
        lapis --lua new
        lapis server
        """
        cmd = self._replace(cmd)
        cmds = [j.servers.startupcmd.get("test_openresty", cmd_start=cmd, ports=[8080], process_strings_regex="^nginx")]
        return cmds

    def test(self):
        """
        kosmos 'j.builders.runtimes.lua.test()'

        server is running on port 8080

        """

        if self.running():
            self.stop()
        self.start()
        self._log_info("openresty is running on port 8080")
        # we now have done a tcp test, lets do a http client connection
        out = j.clients.http.get("http://localhost:8080")

        assert out.find("Welcome to Lapis 1.7.0") != -1  # means message is there
        self.stop()

        self._log_info("openresty test was ok,no longer running")