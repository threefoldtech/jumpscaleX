from Jumpscale import j
from time import sleep


class BuilderMongodb(j.builders.system._BaseClass):
    NAME = "mongod"

    def install(self, start=True, reset=False):
        """
        download, install, move files to appropriate places, and create relavent configs
        """
        if self._done_check("install", reset):
            return

        if j.core.platformtype.myplatform.platform_is_osx:
            j.sal.process.execute("brew uninstall mongodb", die=False)

        appbase = "%s/" % j.builders.tools.dir_paths["BINDIR"]
        j.core.tools.dir_ensure(appbase)

        url = None
        if j.core.platformtype.myplatform.isUbuntu:
            url = "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu1604-3.4.0.tgz"
            dest = "{DIR_TEMP}/mongodb-linux-x86_64-ubuntu1604-3.4.0/bin/"
        elif j.builders.tools.isArch:
            j.builders.system.package.ensure("mongodb")
        elif j.core.platformtype.myplatform.platform_is_osx:
            url = "https://fastdl.mongodb.org/osx/mongodb-osx-ssl-x86_64-3.4.0.tgz"
            dest = "{DIR_TEMP}/mongodb-osx-x86_64-3.4.0/bin/"
        else:
            raise j.exceptions.RuntimeError("unsupported platform")

        if url:
            self._log_info("Downloading mongodb.")
            j.builders.tools.file_download(url, to="{DIR_TEMP}", overwrite=False, expand=True)
            tarpaths = j.builders.tools.find("{DIR_TEMP}", recursive=False, pattern="*mongodb*.tgz", type="f")
            if len(tarpaths) == 0:
                raise j.exceptions.Input(
                    message="could not download:%s, did not find in %s" % (url, self._replace("{DIR_TEMP}"))
                )
            tarpath = tarpaths[0]
            j.builders.tools.file_expand(tarpath, "{DIR_TEMP}")

            for file in j.builders.tools.find(dest, type="f"):
                j.builders.tools.file_copy(file, appbase)

        j.core.tools.dir_ensure("{DIR_VAR}/data/mongodb")
        self._done_set("install")
        if start:
            self.start(reset=reset)

    def build(self, start=True, reset=False):
        raise RuntimeError("not implemented")

    def start(self, reset=False):
        if self.isStarted() and not reset:
            return
        j.core.tools.dir_ensure("{DIR_VAR}/data/mongodb")
        cmd = "mongod --dbpath '{DIR_VAR}/data/mongodb'"
        j.builders.system.process.kill("mongod")
        pm = j.builders.system.processmanager.get()
        pm.ensure(name="mongod", cmd=cmd, env={}, path="", autostart=True)

    def stop(self):
        pm = j.builders.system.processmanager.get()
        pm.stop("mongod")
