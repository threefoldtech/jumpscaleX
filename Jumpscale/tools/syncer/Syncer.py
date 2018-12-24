from Jumpscale import j
import time
from watchdog.observers import Observer
from .MyFileSystemEventHandler import MyFileSystemEventHandler


class Syncer(j.application.JSBaseConfigClass):
    _SCHEMATEXT = """
        @url = jumpscale.syncer.1
        name* = "" (S)
        addr* = "" (S)
        port = 0 (I)
        """

    def _init(self):

        self.PATHS_DEFAULT = ["{DIR_CODE}/github/threefoldtech/jumpscaleX",
                              "{DIR_CODE}/github/threefoldtech/digitalmeX"]

        self.IGNOREDIR = [".git", ".github"]
        self._executor = None
        j.tools.syncer.syncers[self.name] = self

    @property
    def executor(self):
        if not self._executor:
            sshkey = j.clients.sshkey.get()
            sshclient = j.clients.ssh.get("syncer_%s" % self.name, addr=self.addr, port=self.port,
                                          sshkey_name=sshkey.name)
            self._executor = j.tools.executor.ssh_get(sshclient)
        return self._executor

    def sync(self, monitor=False, paths=None):
        """
        sync all code to the remote destinations, uses config as set in jumpscale.toml

        paths is [path1, path2,...] or [["/src",'/dest'],["/src2",'/dest2']]

        can use {} (the dir paths in the dir's

        PATHS_DEFAULT =["{DIR_CODE}/github/threefoldtech/jumpscaleX",
                     "{DIR_CODE}/github/threefoldtech/digitalmeX"]

        """
        if paths is None:
            paths = self.PATHS_DEFAULT

        for item in paths:
            if j.data.types.list.check(item):
                source = j.core.tools.text_replace(item[0])
                dest = self.executor.replace(item[1])
            else:
                source = j.core.tools.text_replace(item)
                dest = self.executor.replace(item)

            self.executor.upload(source, dest, recursive=True, createdir=True,
                                 rsyncdelete=True, ignoredir=self.IGNOREDIR, ignorefiles=None)

        if monitor:
            self._monitor(paths=paths)

    def _monitor(self, paths):
        """
        look for changes in directories which are being pushed & if found push to remote nodes

        paths is [path1, path2,...] or [["/src",'/dest'],["/src2",'/dest2']]

        js_shell 'j.tools.develop.monitor()'

        """

        event_handler = MyFileSystemEventHandler(paths=paths, zoscontainer=self)
        observer = Observer()
        for source in paths:
            if j.data.types.list.check(source):
                source = source[0]
            self._logger.info("monitor:%s" % source)
            source2 = j.core.builder.core.replace(source)
            observer.schedule(event_handler, source2, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
