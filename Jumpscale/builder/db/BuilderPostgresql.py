from Jumpscale import j

builder_method = j.builders.system.builder_method


class BuilderPostgresql(j.builders.system._BaseClass):
    NAME = "psql"

    def _init(self):
        self.DOWNLOAD_DIR = self.tools.joinpaths(self.DIR_BUILD, "build")
        self.DATA_DIR = self._replace("{DIR_BASE}/apps/psql/data")

    @builder_method()
    def build(self):
        postgres_url = "https://ftp.postgresql.org/pub/source/v9.6.13/postgresql-9.6.13.tar.gz"
        j.builders.tools.file_download(postgres_url, to=self.DOWNLOAD_DIR, overwrite=False, expand=True)
        j.builders.system.package.ensure(["build-essential", "zlib1g-dev", "libreadline-dev", "sudo"])

        cmd = self._replace(
            """
            cd {DOWNLOAD_DIR}/postgresql-9.6.13
            ./configure --prefix={DIR_BASE}
            make
        """
        )
        self._execute(cmd)

    @builder_method()
    def install(self, port=5432):
        cmd = self._replace(
            """
            cd {DOWNLOAD_DIR}/postgresql-9.6.13
            make install
        """
        )
        self._execute(cmd)

        if not self.tools.group_exists("postgres"):
            self._execute(
                'adduser --system --quiet --home {DIR_BASE} --no-create-home \
        --shell /bin/bash --group --gecos "PostgreSQL administrator" postgres'
            )

        self._remove(self.DATA_DIR)

        c = self._replace(
            """
            cd {DIR_BASE}
            mkdir -p log
            mkdir -p {DATA_DIR}
            chown -R postgres {DATA_DIR}
            sudo -u postgres {DIR_BIN}/initdb -D {DATA_DIR} -E utf8 --locale=en_US.UTF-8
        """
        )
        self._execute(c)

    @property
    def startup_cmds(self):
        pg_ctl = self._replace("sudo -u postgres {DIR_BIN}/pg_ctl %s -D {DATA_DIR}")
        cmd_start = pg_ctl % "start"
        cmd_stop = pg_ctl % "stop"
        cmd = j.tools.startupcmd.get("postgres", cmd_start, cmd_stop, ports=[5432], path="/sandbox/bin")
        return [cmd]

    def test(self):
        if self.running():
            self.stop()

        self.start()
        _, response, _ = self._execute("pg_isready", showout=False)
        assert "accepting connections" in response

        self.stop()
        print("TEST OK")

    @builder_method()
    def sandbox(self):
        self.PACKAGE_DIR = self._replace("{DIR_SANDBOX}/sandbox")
        self.tools.dir_ensure(self.PACKAGE_DIR)
        # data dir
        self.tools.dir_ensure("%s/apps/psql/data" % self.PACKAGE_DIR)
        self._execute(
            """
            cd {DOWNLOAD_DIR}/postgresql-9.6.13
            make install DESTDIR={DIR_SANDBOX}
            """
        )

        bins_dir = self._replace("{PACKAGE_DIR}/bin")
        j.tools.sandboxer.libs_clone_under(bins_dir, self.DIR_SANDBOX)

        # startup.toml
        templates_dir = self.tools.joinpaths(j.sal.fs.getDirName(__file__), "templates")
        startup_path = self._replace("{DIR_SANDBOX}/.startup.toml")
        self._copy(self.tools.joinpaths(templates_dir, "postgres_startup.toml"), startup_path)
