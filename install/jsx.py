#!/usr/bin/env python3
import os

os.environ["LC_ALL"] = "en_US.UTF-8"
import click

import argparse
import inspect
import time
import os
import shutil
import sys
from importlib import util
from urllib.request import urlopen

DEFAULT_BRANCH = "master"


def load_install_tools():
    # get current install.py directory
    path = "/sandbox/code/github/threefoldtech/jumpscaleX/install/InstallTools.py"
    if not os.path.exists(path):
        rootdir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(rootdir, "InstallTools.py")

        if not os.path.exists(path) or path.find("/code/") == -1:
            url = (
                "https://raw.githubusercontent.com/threefoldtech/jumpscaleX/%s/install/InstallTools.py" % DEFAULT_BRANCH
            )
            with urlopen(url) as resp:
                if resp.status != 200:
                    raise RuntimeError("fail to download InstallTools.py")
                with open(path, "w+") as f:
                    f.write(resp.read().decode("utf-8"))
                print("DOWNLOADED INSTALLTOOLS TO %s" % path)

    spec = util.spec_from_file_location("IT", path)
    IT = spec.loader.load_module()
    sys.excepthook = IT.my_excepthook
    check_branch(IT)
    return IT


def check_branch(IT):
    HOMEDIR = os.environ["HOME"]
    paths = ["/sandbox/code/github/threefoldtech/jumpscaleX", "%s/code/github/threefoldtech/jumpscaleX" % HOMEDIR]
    for path in paths:
        if os.path.exists(path):
            cmd = "cd %s; git branch | grep \* | cut -d ' ' -f2" % path
            rc, out, err = IT.Tools.execute(cmd)
            if out.strip() != DEFAULT_BRANCH:
                print("cannot install, the branch of jumpscale in %s needs to be %s" % (path, DEFAULT_BRANCH))
                sys.exit(1)


def jumpscale_get(die=True):
    # jumpscale need to be available otherwise cannot do
    try:
        from Jumpscale import j
    except Exception as e:
        if die:
            print("ERROR: cannot use jumpscale yet, has not been installed")
            sys.exit(1)
        return None
    return j


@click.group()
def cli():
    pass


### CONFIGURATION (INIT) OF JUMPSCALE ENVIRONMENT
@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if /sandbox exists otherwise ~/sandbox")
@click.option("--codedir", default=None, help="path where the github code will be checked out, default sandbox/code")
@click.option(
    "--basedir",
    default=None,
    help="path where JSX will be installed default /sandbox if /sandbox exists otherwise ~/sandbox",
)
@click.option("--no-sshagent", is_flag=True, help="do you want to use an ssh-agent")
@click.option(
    "--sshkey", default=None, is_flag=True, type=bool, help="if more than 1 ssh-key in ssh-agent, specify here"
)
@click.option("--debug", is_flag=True, help="do you want to put kosmos in debug mode?")
@click.option("--no-interactive", is_flag=True, help="default is interactive")
@click.option(
    "--privatekey",
    default=False,
    help="24 words, use '' around the private key if secret specified and private_key not then will ask in -y mode will autogenerate",
)
@click.option(
    "-s", "--secret", default=None, help="secret for the private key (to keep secret), default will get from ssh-key"
)
def configure(
    basedir=None,
    codedir=None,
    debug=False,
    sshkey=None,
    no_sshagent=False,
    no_interactive=False,
    privatekey=None,
    secret=None,
    configdir=None,
):
    """
    initialize 3bot (JSX) environment
    """

    return _configure(
        basedir=basedir,
        codedir=codedir,
        debug=debug,
        sshkey=sshkey,
        no_sshagent=no_sshagent,
        no_interactive=no_interactive,
        privatekey_words=privatekey,
        secret=secret,
    )


# have to do like this, did not manage to call the click enabled function (don't know why)
def _configure(
    basedir=None,
    codedir=None,
    debug=False,
    sshkey=None,
    no_sshagent=False,
    no_interactive=False,
    privatekey_words=None,
    secret=None,
    configdir=None,
):
    interactive = not no_interactive
    sshagent_use = not no_sshagent
    IT.MyEnv.configure(
        basedir=basedir,
        readonly=None,
        codedir=codedir,
        sshkey=sshkey,
        sshagent_use=sshagent_use,
        debug_configure=debug,
        interactive=interactive,
        secret=secret,
        configdir=configdir,
    )
    j = jumpscale_get(die=False)

    if not j and privatekey_words:
        print(
            "cannot load jumpscale, \
            can only configure private key when jumpscale is installed locally use jsx install..."
        )
        sys.exit(1)

    if j:
        j.data.nacl.configure(privkey_words=privatekey_words)


### INSTALL OF JUMPSCALE IN CONTAINER ENVIRONMENT
@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option(
    "-s", "--scratch", is_flag=True, help="from scratch, means will start from empty ubuntu and re-install everything"
)
@click.option("-d", "--delete", is_flag=True, help="if set will delete the docker container if it already exists")
@click.option("-w", "--wiki", is_flag=True, help="also install the wiki system")
@click.option("--portrange", default=1, help="portrange, leave empty unless you know what you do.")
@click.option(
    "--image",
    default=None,
    help="select the container image to use to create the container, leave empty unless you know what you do (-:",
)
@click.option(
    "-b", "--branch", default=None, help="jumpscale branch. default 'master' or 'development' for unstable release"
)
@click.option(
    "--pull",
    is_flag=True,
    help="pull code from git, if not specified will only pull if code directory does not exist yet",
)
@click.option(
    "-r",
    "--reinstall",
    is_flag=True,
    help="reinstall, basically means will try to re-do everything without removing the data",
)
@click.option("--no_interactive", is_flag=True, help="default is interactive")
def container_install(
    name="3bot",
    scratch=False,
    delete=True,
    wiki=False,
    portrange=1,
    image=None,
    branch=None,
    reinstall=False,
    no_interactive=False,
    pull=False,
    configdir=None,
):
    """
    create the 3bot container and install jumpcale inside
    if interactive is True then will ask questions, otherwise will go for the defaults or configured arguments

    if you want to configure other arguments use 'jsx configure ... '


    """
    interactive = not no_interactive

    _configure(configdir=configdir)

    if scratch:
        image = "phusion/baseimage"
    if not image:
        image = "despiegk/3bot"

    docker = IT.DockerContainer(name=name, delete=delete, portrange=portrange, image=image)

    docker.install()

    docker.jumpscale_install(branch=branch, redo=reinstall, pull=pull, wiki=wiki)


def container_get(name="3bot", existcheck=True, portrange=1, delete=False):
    docker = IT.DockerContainer(name=name, delete=delete, portrange=portrange)
    if existcheck:
        if name not in IT.DockerFactory.containers_running():
            # means is not running yet
            if name not in IT.DockerFactory.containers_names():
                docker.install()
                docker.jumpscale_install()
                # needs to stay because will make sure that the config is done properly in relation to your shared folders from the host
            else:
                docker.start()
                time.sleep(1)
    return docker


### INSTALL OF JUMPSCALE IN CONTAINER ENVIRONMENT
@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-w", "--wiki", is_flag=True, help="also install the wiki system")
@click.option("--no_sshagent", is_flag=True, help="do you want to use an ssh-agent")
@click.option(
    "-b", "--branch", default=None, help="jumpscale branch. default 'master' or 'development' for unstable release"
)
@click.option(
    "--pull",
    is_flag=True,
    help="pull code from git, if not specified will only pull if code directory does not exist yet",
)
@click.option(
    "-r",
    "--reinstall",
    is_flag=True,
    help="reinstall, basically means will try to re-do everything without removing the data",
)
def install(wiki=False, branch=None, reinstall=False, pull=False, no_sshagent=False, configdir=None):
    """
    install jumpscale in the local system (only supported for Ubuntu 18.04+ and mac OSX, use container install method otherwise.
    if interactive is True then will ask questions, otherwise will go for the defaults or configured arguments

    if you want to configure other arguments use 'jsx configure ... '

    """

    _configure(configdir=configdir, basedir="/sandbox", no_sshagent=no_sshagent)
    SANDBOX = IT.MyEnv.config["DIR_BASE"]
    if reinstall:
        # remove the state
        IT.MyEnv.state_reset()
        force = True
    else:
        force = False

    installer = IT.JumpscaleInstaller(branch=branch)
    installer.install(sandboxed=False, force=force, gitpull=pull)
    if wiki:
        IT.Tools.execute("source %s/env.sh;kosmos 'j.builder.db.zdb.install()'" % SANDBOX, showout=True)
        IT.Tools.execute("source %s/env.sh;kosmos 'j.builder.runtimes.lua.install()'" % SANDBOX, showout=True)
    print("Jumpscale X installed successfully")


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-i", "--imagename", default="despiegk/3bot", help="name of image where we will import to")
@click.option("-p", "--path", default=None, help="image location")
@click.option("--no-start", is_flag=True, help="container will start auto")
def container_import(name="3bot", path=None, imagename="despiegk/3bot", no_start=False, configdir=None):
    """
    import container from image file, if not specified will be /tmp/3bot.tar
    :param args:
    :return:
    """
    start = not no_start
    docker = container_get(existcheck=False)
    docker.import_(path=path, imagename=imagename, start=start)


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-p", "--path", default=None, help="image location")
@click.option("--no-overwrite", is_flag=True, help="std container will overwrite the existing one")
@click.option("--skip-if-exists", is_flag=True, help="std container will overwrite the existing one")
def container_export(name="3bot", path=None, no_overwrite=False, skip_if_exists=False, configdir=None):
    """
    export the 3bot to image file, if not specified will be /tmp/3bot.tar
    :param name:
    :param path:
    :return:
    """
    overwrite = not no_overwrite
    _configure(configdir=configdir)
    docker = container_get(name=name)
    docker.export(path=path, skip_if_exists=skip_if_exists, overwrite=overwrite)


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_clean(name="3bot", configdir=None):
    """
    starts from an export, if not there will do the export first
    :param name:
    :param path:
    :return:
    """
    _configure(configdir=configdir)
    docker = container_get(name=name)
    docker.clean()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_stop(name="3bot", configdir=None):
    """
    stop the 3bot container
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    docker = container_get(name=name, existcheck=False)
    docker.stop()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_start(name="3bot", configdir=None):
    """
    start the 3bot container
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    docker = container_get(name=name, existcheck=False)
    docker.start()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_delete(name="3bot", configdir=None):
    """
    delete the 3bot container
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    docker = container_get(name=name, existcheck=False)
    docker.delete()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
def containers_reset(configdir=None):
    """
    remove all docker containers
    :param name:
    :return:
    """
    _configure(configdir=configdir)
    IT.DockerFactory.reset()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_kosmos(name="3bot", configdir=None):
    """
    open a kosmos shell in container
    :param name: name of container if not the default =  3bot
    :return:
    """
    docker = container_get(name=name)
    os.execv(
        shutil.which("ssh"),
        [
            "ssh",
            "root@localhost",
            "-A",
            "-t",
            "-oStrictHostKeyChecking=no",
            "-p",
            str(docker.config.sshport),
            "source /sandbox/env.sh;kosmos",
        ],
    )


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-t", "--target", default="auto", help="auto,local,container, default is auto will try container first")
def kosmos(name="3bot", target="auto", configdir=None):
    j = jumpscale_get(die=True)
    j.application.interactive = True
    n = j.data.nacl.get(load=False)  # important to make sure private key is loaded
    if n.load(die=False) is False:
        n.configure()
    j.application.bcdb_system  # needed to make sure we have bcdb running, needed for code completion
    j.shell(loc=False, locals_=locals(), globals_=globals())


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def container_shell(name="3bot", configdir=None):
    """
    open a  shell to the container for 3bot
    :param name: name of container if not the default
    :return:
    """

    docker = container_get(name=name)
    os.execv(
        shutil.which("ssh"),
        ["ssh", "root@localhost", "-A", "-t", "-oStrictHostKeyChecking=no", "-p", str(docker.config.sshport)],
    )


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
def wireguard(configdir=None):
    """
    jsx wireguard
    enable wireguard, can be on host or server
    :return:
    """
    name = "3bot"
    if not IT.DockerFactory.indocker():
        docker = container_get(name=name)
        # remotely execute wireguard
        docker.sshexec("source /sandbox/env.sh;jsx wireguard")
    wg = IT.WireGuard()

    if IT.DockerFactory.indocker():
        wg.server_start()
    else:
        docker.wireguard.connect()


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("--url", default="3bot", help="git url e.g. https://github.com/myfreeflow/kosmos")
def modules_install(url=None, configdir=None):
    """
    install jumpscale module in local system
    :return:
    """
    from Jumpscale import j

    path = j.clients.git.getContentPathFromURLorPath(url)
    _generate(path=path)


@click.command()
# @click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def bcdb_indexrebuild(name=None, configdir=None):
    """
    rebuilds the index for all BCDB or a chosen one (with name),
    use this to fix corruption issues with index
    if name is not given then will walk over all known BCDB's and rebuild index
    :return:
    """
    from Jumpscale import j

    j.shell()
    bcdb.index_rebuild()


@click.command()
def generate():
    """
    generate the loader file, important to do when new modules added
    """
    _generate()


def _generate(path=None):
    j = jumpscale_get(die=True)
    j.sal.fs.remove("{DIR_VAR}/codegen")
    j.sal.fs.remove("{DIR_VAR}/cmds")
    from Jumpscale.core.generator.JSGenerator import JSGenerator
    from Jumpscale import j

    g = JSGenerator(j)

    if path:
        # means we need to link
        g.lib_link(path)
    g.generate(methods_find=True)
    g.report()
    print("OK ALL DONE, GOOD LUCK (-:")


if __name__ == "__main__":

    cli.add_command(configure)
    cli.add_command(install)
    cli.add_command(kosmos)
    cli.add_command(generate)
    cli.add_command(wireguard)
    cli.add_command(modules_install)
    cli.add_command(bcdb_indexrebuild)

    # DO NOT DO THIS IN ANY OTHER WAY !!!
    IT = load_install_tools()

    IT.MyEnv.init()  # will take into consideration the --configdir

    if not IT.DockerFactory.indocker():
        cli.add_command(container_kosmos)
        cli.add_command(container_install)
        cli.add_command(container_stop)
        cli.add_command(container_start)
        cli.add_command(container_delete)
        cli.add_command(containers_reset)
        cli.add_command(container_export)
        cli.add_command(container_import)
        cli.add_command(container_shell)
        cli.add_command(container_clean)

    cli()
