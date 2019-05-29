import click

import argparse
import inspect
import os
import shutil
import sys
from importlib import util
from urllib.request import urlopen

DEFAULT_BRANCH = "development_installer"

# CONTAINER_BASE_IMAGE = "phusion/baseimage:master"
# CONTAINER_BASE_IMAGE = "despiegk/3bot:latest"


def load_install_tools():
    # get current install.py directory
    rootdir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(rootdir, "InstallTools.py")

    if not os.path.exists(path):
        os.chdir(rootdir)
        url = "https://raw.githubusercontent.com/threefoldtech/jumpscaleX/%s/install/InstallTools.py" % DEFAULT_BRANCH
        with urlopen(url) as resp:
            if resp.status != 200:
                raise RuntimeError("fail to download InstallTools.py")
            with open(path, "w+") as f:
                f.write(resp.read().decode("utf-8"))

    spec = util.spec_from_file_location("IT", path)
    IT = spec.loader.load_module()
    sys.excepthook = IT.my_excepthook
    return IT


@click.group()
def cli():
    pass


### CONFIGURATION (INIT) OF JUMPSCALE ENVIRONMENT
@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg")
@click.option(
    "--codedir",
    default=None,
    help="path where the github code will be checked out, default /sandbox/code",
)
@click.option(
    "--basedir",
    default=None,
    help="path where JSX will be installed default /sandbox",
)
@click.option("--no_sshagent", is_flag=True, help="do you want to use an ssh-agent")
@click.option(
    "--sshkey", default=None, is_flag=True, type=bool, help="if more than 1 ssh-key in ssh-agent, specify here"
)
@click.option("--debug", is_flag=True, help="do you want to put kosmos in debug mode?")
@click.option("--no_interactive", is_flag=True, help="default is interactive")
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
    configdir=None,
    codedir=None,
    debug=False,
    sshkey=None,
    no_sshagent=False,
    no_interactive=False,
    privatekey_words=None,
    secret=None,
):
    """
    initialize 3bot (JSX) environment
    """

    return _configure(
        basedir=basedir,
        configdir=configdir,
        codedir=codedir,
        debug=debug,
        sshkey=sshkey,
        no_sshagent=no_sshagent,
        no_interactive=no_interactive,
        privatekey_words=privatekey_words,
        secret=secret,
    )

#have to do like this, did not manage to call the click enabled function (don't know why)
def _configure(
    basedir=None,
    configdir=None,
    codedir=None,
    debug=False,
    sshkey=None,
    no_sshagent=False,
    no_interactive=False,
    privatekey_words=None,
    secret=None,
):
    interactive = not no_interactive
    sshagent_use = not no_sshagent
    IT.MyEnv.configure(
        configdir=configdir,
        basedir=basedir,
        readonly=None,
        codedir=codedir,
        sshkey=sshkey,
        sshagent_use=sshagent_use,
        debug_configure=debug,
        interactive=interactive,
        secret=secret,
    )

    # jumpscale need to be available otherwise cannot do
    j = False
    try:
        from Jumpscale import j
    except Exception as e:
        pass

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
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-i", "--interactive", is_flag=True, help="will ask questions in interactive way, otherwise auto values")
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
def container(
    name="3bot",
    configdir=None,
    scratch=False,
    delete=True,
    wiki=False,
    portrange=1,
    image="despiegk/3bot",
    branch=None,
    reinstall=False,
    no_interactive=False,
    pull=False,
):
    """
    create the 3bot container and install jumpcale inside
    if interactive is True then will ask questions, otherwise will go for the defaults or configured arguments
    """
    interactive = not no_interactive
    IT.Tools.shell()
    if not args.s and not args.y and not args.r:
        if IT.Tools.ask_yes_no("\nDo you want to redo the full install? (means redo pip's ...)"):
            args.r = True

        if CONTAINER_NAME in IT.Docker.docker_names() and args.d is False and args.y is False:
            args.d = IT.Tools.ask_yes_no(
                "docker:%s exists, ok to remove? Will otherwise keep and install inside." % CONTAINER_NAME
            )

    if args.pull is None:
        if args.y is False:
            args.pull = IT.Tools.ask_yes_no("Do you want to pull code changes from git?")
        else:
            args.pull = False  # default is not pull

    if not args.secret:
        if args.y:
            args.secret = IT.MyEnv.sshagent_sshkey_pub_get() if IT.MyEnv.sshagent_active_check() else "1234"
        else:
            if IT.MyEnv.sshagent_active_check():
                args.secret = IT.Tools.ask_string(
                    "Optional: provide secret to use for passphrase, if ok to use SSH-Agent just press 'ENTER'",
                    default="SSH",
                )
            else:
                args.secret = IT.Tools.ask_string("please provide secret passphrase for the BCDB.", default="1234")

    if not args.private_key and not args.y:
        args.private_key = IT.Tools.ask_string(
            "please provide 24 words of the private key, or just press 'ENTER' for autogeneration."
        )
    install_summary(args)
    docker = IT.Docker(name=name, delete=delete, portrange=portrange, image=image)
    docker.install()


def docker_get(name="3bot", existcheck=True, portrange=1, delete=False):
    docker = IT.Docker(name=name, delete=delete, portrange=portrange)
    if existcheck and CONTAINER_NAME not in docker.docker_names():
        print("container does not exists. please install first")
        sys.exit(1)
    return docker


### INSTALL OF JUMPSCALE IN CONTAINER ENVIRONMENT
@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-w", "--wiki", is_flag=True, help="also install the wiki system")
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
def install(configdir=None, wiki=False, branch=None, reinstall=False, pull=False):
    """
    install jumpscale in the local system (only supported for Ubuntu 18.04+ and mac OSX, use container install method otherwise.
    if interactive is True then will ask questions, otherwise will go for the defaults or configured arguments

    if you want to configure other arguments use 'jsx configure ... '

    """

    _configure(configdir=configdir)

    if reinstall:
        # remove the state
        IT.MyEnv.state_reset()
        pull = True
        force = True
    else:
        force = False

    installer = IT.JumpscaleInstaller(branch=branch)
    installer.install(sandboxed=False, force=force, gitpull=pull)
    if wiki:
        IT.Tools.shell()
        IT.Tools.execute("source %s/env.sh;kosmos 'j.tools.markdowndocs.test()'" % SANDBOX, showout=False)
    print("Jumpscale X installed successfully")


def docker_get(name="3bot", existcheck=True, portrange=1, delete=False):
    docker = IT.Docker(name=name, delete=delete, portrange=portrange)
    if existcheck and CONTAINER_NAME not in docker.docker_names():
        print("container does not exists. please install first")
        sys.exit(1)
    return docker


@click.command(name="import")
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-p", "--path", default="/tmp/3bot.tar", help="image location")
def import_(name="3bot", path="/tmp/3bot.tar", configdir=None):
    """
    import container from image file, if not specified will be /tmp/3bot.tar
    :param args:
    :return:
    """
    docker = docker_get(existcheck=False)
    docker.import_(path=args.input)


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
@click.option("-p", "--path", default="/tmp/3bot.tar", help="image location")
def export(name="3bot", path="/tmp/3bot.tar", configdir=None):
    """
    export the 3bot to image file, if not specified will be /tmp/3bot.tar
    :param name:
    :param path:
    :return:
    """
    docker = docker_get(name=name)
    docker.export(path=args.output)


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def stop(name="3bot", configdir=None):
    """
    stop the 3bot container
    :param name:
    :return:
    """
    docker = docker_get(name=name, existcheck=False)
    docker.stop()


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def start(name="3bot", configdir=None):
    """
    start the 3bot container
    :param name:
    :return:
    """
    docker = docker_get(name=name, existcheck=False)
    docker.start()


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def delete(name="3bot", configdir=None):
    """
    delete the 3bot container
    :param name:
    :return:
    """
    docker = docker_get(name=name, existcheck=False)
    docker.delete()


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
def reset(configdir=None):
    """
    remove all docker containers as well as current configuration of the JSX environment
    :param name:
    :return:
    """
    Tools.shell()


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
# @click.option("-t", "--target", default="auto", help="auto,local,container, default is auto will try container first")
def kosmos(name="3bot", target="auto", configdir=None):
    """
    open a kosmos shell, if container is running will use the container, if installed locally will use local kosmos
    :param name: name of container if not the default
    :return:
    """
    docker = docker_get(name=name)
    os.execv(
        shutil.which("ssh"),
        [
            "ssh",
            "root@localhost",
            "-A",
            "-t",
            "-oStrictHostKeyChecking=no",
            "-p",
            str(docker.port),
            "source /sandbox/env.sh;kosmos",
        ],
    )


@click.command()
@click.option("--configdir", default=None, help="default /sandbox/cfg if it exists otherwise ~/sandbox/cfg")
@click.option("-n", "--name", default="3bot", help="name of container")
def shell(name="3bot", configdir=None):
    """
    open a  shell to the container for 3bot
    :param name: name of container if not the default
    :return:
    """

    docker = docker_get(name=name)
    os.execv(
        shutil.which("ssh"), ["ssh", "root@localhost", "-A", "-t", "-oStrictHostKeyChecking=no", "-p", str(docker.port)]
    )


@click.command()
def generate():
    """
    generate the loader file, important to do when new modules added
    """
    j.sal.fs.remove("{DIR_VAR}/codegen")
    j.sal.fs.remove("{DIR_VAR}/cmds")
    from Jumpscale.core.generator.JSGenerator import JSGenerator
    from Jumpscale import j

    g = JSGenerator(j)
    g.generate(methods_find=True)
    g.report()


if __name__ == "__main__":

    cli.add_command(configure)
    cli.add_command(install)
    cli.add_command(container)
    cli.add_command(stop)
    cli.add_command(start)
    cli.add_command(delete)
    cli.add_command(reset)
    cli.add_command(export)
    cli.add_command(import_)
    cli.add_command(shell)
    cli.add_command(kosmos)
    cli.add_command(generate)

    # DO NOT DO THIS IN ANY OTHER WAY !!!
    IT = load_install_tools()

    IT.MyEnv.init()  # will take into consideration the --configdir

    cli()