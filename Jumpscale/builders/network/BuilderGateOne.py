from Jumpscale import j




class BuilderGateOne(j.builder.system._BaseClass):
    NAME = "gateone"

    def build(self, reset=False):
        """
        Build Gateone
        :param reset: reset build if already built before
        :return:
        """
        if self.doneCheck("build", reset):
            return

        j.clients.git.pullGitRepo("https://github.com/liftoff/GateOne", branch="master")

        self.doneSet('build')

    def install(self, reset=False):
        """
        Installs gateone

        @param reset: boolean: forces the install operation.
    
        """
        if reset is False and self.isInstalled():
            return

        cmd = """
cd /opt/code/github/liftoff/GateOne
apt-get install build-essential python3-dev python3-setuptools python3-pip -y
pip3 install tornado==4.5.3
python3 setup.py install
cp /usr/local/bin/gateone {DIR_BIN}/gateone
ln -s /usr/bin/python3 /usr/bin/python
"""
        j.sal.process.execute(cmd)
        j.builder.system.ssh.keygen(name="id_rsa")
        self.doneSet('install')

    def start(self, name="main", address="localhost", port=10443):

        """
        Starts gateone.

        @param name: str: instance name.
        @param address: str: bind address.
        @param port: int: port number.

        """
        cmd = "eval `ssh-agent -s` ssh-add /root/.ssh/id_rsa && gateone --address={} --port={} --disable_ssl".format(address, port)
        pm = j.builder.system.processmanager.get()
        pm.ensure(name='gateone_{}'.format(name), cmd=cmd)

    def stop(self, name='main'):
        """
        Stops gateone 
        """
        pm = j.builder.system.processmanager.get()
        pm.stop(name='gateone_{}'.format(name))

    def restart(self, name="main"):
        """
        Restart GateOne instance by name.
        """
        self.stop(name)
        self.start(name)

    def reset(self):
        """
        helper method to clean what this module generates.
        """
        pass
