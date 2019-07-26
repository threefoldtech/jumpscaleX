from Jumpscale import j


def main(self):
    """
    to run:

    kosmos 'j.data.bcdb.test(name="fs")'

    """
    tags = ["color:blue", "color:white", "font:arial", "font:tahoma", "style:italian"]
    types = ["md", "pdf", "xls", "doc", "jpg"]
    contents = ["threefold foundation", "the new internet", "change the world", "digital freedom", "the future of IT"]
    bcdb = j.data.bcdb.get("test_fs")
    bcdb.reset()
    cl = j.clients.sonic.get_client_bcdb()
    cl.flush("test_fs")
    file_model = bcdb.model_get_from_file("{}/models_system/FILE.py".format(self._dirpath_))
    dir_model = bcdb.model_get_from_file("{}/models_system/DIR.py".format(self._dirpath_))

    root = dir_model.new()
    root.name = "/"
    root.save()

    for i in range(1, 6):

        parent = dir_model.new()
        parent.name = "{}{}/".format(root.name, i)
        parent.save()
        root.dirs.append(parent.id)

        # create subdirs
        for k in range(1, 6):
            subdir = dir_model.new()
            subdir.name = "{}dir_{}/".format(parent.name, k)
            subdir.save()
            parent.dirs.append(subdir.id)

        # create files
        for k in range(1, 6):
            file = file_model.new()
            file.name = "{}file_{}".format(parent.name, k)
            file.content = contents[(k - 1) % 5]
            file.type = types[(k - 1) % 5]
            file.tags.append(tags[(k - 1) % 5])
            file.dir_id = parent.id
            file.save()
            parent.files.append(file.id)

        parent.save()
    root.save()
    res = file_model.files_search(tags="color:blue")
    assert len(res) == 5
    res = file_model.files_search(type="md")
    assert len(res) == 5
    res = file_model.files_search(content="threefold")
    assert len(res) == 5
    res = file_model.files_search(tags="color:blue", type="pdf")
    assert len(res) == 0
    res = file_model.files_search(tags="color:blue", type="md")
    assert len(res) == 5

    start_cmd = """
from Jumpscale import j
rack = j.servers.rack.get()
from jumpscale.Jumpscale.data.bcdb.connectors.webdav.BCDBFSProvider import BCDBFSProvider

rack.webdav_server_add(webdavprovider=BCDBFSProvider("test_fs"), port=4444)
rack.start()
"""

    s = j.servers.startupcmd.get(
        name="webdav_fs_test", cmd_start=start_cmd, interpreter="python", executor="tmux", ports=[4444]
    )
    s.start()
    print("Dav server running on port 4444")
