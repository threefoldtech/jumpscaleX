from Jumpscale import j
from wsgidav import compat, util
from wsgidav.dav_provider import DAVCollection, DAVNonCollection, DAVProvider


class DirCollection(DAVCollection):
    """
    Handles all kinds of directory-like resources
    """

    def __init__(self, path, environ):
        DAVCollection.__init__(self, path, environ)

        self.obj = self.provider.get_by_name(path)
        self._files = {}
        self._dirs = {}
        self._init_members()

    def _init_members(self):
        self._files = {}
        self._dirs = {}
        files = [self.provider._file_model.get(i) for i in self.obj.files]
        dirs = [self.provider._dir_model.get(i) for i in self.obj.dirs]
        for file in files:
            self._files[j.sal.fs.getBaseName(file.name)] = file
        for directory in dirs:
            self._dirs[j.sal.fs.getBaseName(directory.name)] = directory

    def get_member_names(self):
        """
        get member names to be listed from the path
        :return: list of member names
        """
        self._init_members()
        return list(self._files.keys()) + list(self._dirs.keys())

    def get_member(self, name):
        """
        get member by name
        :param name: member name
        :return: DirCollection if the member is a dir-like or DocResource if the member is a doc
        """

        if name in self._dirs:
            return DirCollection(self._dirs[name].name, self.environ)

        if name in self._files:
            path = j.sal.fs.joinPaths(self.obj.name, self._files[name].name)
            return DocResource(path, self.environ, self._files[name])

        return None

    def create_collection(self, name):
        dir = self.provider._dir_model.new()
        name = j.sal.fs.joinPaths(self.path, name + "/")
        dir.name = name
        dir.save()
        self.obj.dirs.append(dir.id)
        self.obj.save()
        return True

    def handle_delete(self):
        parent_name = j.sal.fs.getDirName(self.path)
        parent = self.provider.get_by_name(parent_name)
        parent.dirs.remove(self.obj.id)
        parent.save()
        for name in self.get_member_names():
            member = self.get_member(name)
            member.delete()
        self.obj.delete()
        return True

    def support_recursive_delete(self):
        return True

    def create_empty_resource(self, name):

        new_obj = self.provider._file_model.new()
        new_obj.name = j.sal.fs.joinPaths(self.path, name)
        new_obj.save()
        self.obj.files.append(new_obj.id)
        self.obj.save()
        self._files[name] = new_obj
        return self.get_member(name)


TMP_DIR = "/tmp/dav_tmp"


class DocResource(DAVNonCollection):
    """
    Handles docs. a doc is bcdb data object treated like a documentation
    """

    def __init__(self, path, environ, vfile):
        DAVNonCollection.__init__(self, path, environ)
        self.vfile = vfile
        self.content = self.vfile.content
        self._title = j.sal.fs.getBaseName(self.vfile.name)

    @property
    def title(self):
        return self._title

    def get_content(self):
        html = self.content
        return compat.BytesIO(html.encode("utf-8"))

    def get_content_length(self):
        return len(self.get_content().read())

    def get_content_type(self):
        return self.vfile.content_type

    def get_display_name(self):
        return compat.to_native(self.title)

    def get_display_info(self):
        return {"type": self.vfile.content_type}

    def handle_delete(self):
        self.vfile.delete()
        parent_path = j.sal.fs.getDirName(self.vfile.name)
        parent = self.provider.get_by_path(parent_path)
        parent.children.remove(self.vfile.id)
        parent.save()
        return True

    def begin_write(self, content_type=None):
        j.sal.fs.createEmptyFile(TMP_DIR)
        j.sal.fs.writeFile(TMP_DIR, self.vfile.content)
        return open(TMP_DIR, "wb")

    def end_write(self, with_errors):
        if j.sal.fs.exists(TMP_DIR):
            new_content = j.sal.fs.readFile(TMP_DIR)
            self.vfile.content = new_content
            self.vfile.save()
            j.sal.fs.remove(TMP_DIR)

    def copy_move_single(self, dest_path, is_move):
        new_obj = self.provider._file_model.new()
        new_obj.name = dest_path
        new_obj.content = self.vfile.content
        new_obj.save()
        new_parent_path = j.sal.fs.getDirName(dest_path) or "/"
        parent = self.provider.get_by_path(new_parent_path)
        parent.children.append(new_obj.id)
        if is_move:
            self.delete()
        return True


class BCDBFSProvider(DAVProvider):
    def __init__(self, bcdb_name):
        DAVProvider.__init__(self)
        self._bcdb = j.data.bcdb.get(bcdb_name)
        self._file_model = self._bcdb.model_get_from_file("{}/models_system/FILE.py".format(self._bcdb._dirpath))
        self._dir_model = self._bcdb.model_get_from_file("{}/models_system/DIR.py".format(self._bcdb._dirpath))

    def get_resource_inst(self, path, environ):
        """
        Return DAVResource object for path.
        """
        root = DirCollection("/", environ)
        return root.resolve("/", path)

    def get_by_name(self, name):
        res = self._dir_model.find(name=name)
        if len(res) == 1:
            print("> found one object with path: {}".format(name))
            return res[0]
        elif len(res) > 1:
            print("> found more the one object with path: {}".format(name))
            return res
        else:
            print("> can't find objects for {}".format(name))
            return None
