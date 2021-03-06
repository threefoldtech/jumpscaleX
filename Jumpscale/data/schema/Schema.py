import os
from copy import copy
from .SchemaProperty import SchemaProperty
from Jumpscale import j
import sys
from Jumpscale import j


class SystemProps:
    def __str__(self):
        if len(self.__dict__.items()) > 0:
            out = "\n### systemprops:\n\n"
            for key, item in self.__dict__.items():
                out += str(key) + ":" + str(item) + "\n"
            return out
        return ""

    __repr__ = __str__


class Schema(j.application.JSBaseClass):
    def __init__(self, text, md5=None, url=None):
        j.application.JSBaseClass.__init__(self)
        self.properties = []
        self._systemprops = {}
        self._obj_class = None
        self._capnp = None
        self._index_list = None

        self.systemprops = SystemProps()

        self.url = url

        if md5:
            self._md5 = md5
            assert j.data.schema._md5(text) == self._md5
        else:
            self._md5 = j.data.schema._md5(text)

        self._schema_from_text(text)
        self.key = j.core.text.strip_to_ascii_dense(self.url).replace(".", "_")

        urls = self.url.split(".")
        if len(urls) > 0:
            try:
                # try if last one is version nr, if so pop it
                j.data.types.int.clean(urls[-1])
                self.version = urls.pop(len(urls) - 1)
                # will remove the version from the url
                self.url_noversion = ".".join(self.url.split(".")[:-1])
                if self.url_noversion in j.data.schema.schemas_versionless:
                    if j.data.schema.schemas_versionless[self.url_noversion].version < self.version + 1:
                        # version itself can be replaced as well, there could be an update
                        j.data.schema.schemas_versionless[self.url_noversion] = self
                else:
                    j.data.schema.schemas_versionless[self.url_noversion] = self
            except:
                self.version = None
                self.url_noversion = None
            urls = ".".join(urls)

    @property
    def _path(self):
        return j.sal.fs.getDirName(os.path.abspath(__file__))

    def _error_raise(self, msg, e=None, schema=None):
        if self.url == "" and "url" in self._systemprops:
            self.url = self._systemprops["url"]
        out = "\nerror in schema:\n"
        out += "    url:%s\n" % self.url
        out += "    msg:%s\n" % j.core.text.prefix("    ", msg)
        if schema:
            out += "    schema:\n%s" % schema
        if e is not None:
            out += "\nERROR:\n"
            out += j.core.text.prefix("        ", str(e))
        raise RuntimeError(out)

    def _proptype_get(self, txt):
        """
        if default value specified in the schema, will check how to convert it to a type
        :param txt:
        :return:
        """

        if "\\n" in txt:
            return j.data.types.get("multiline", default=txt)

        if "'" in txt or '"' in txt or txt.strip("'") == "":
            txt = txt.strip().strip('"').strip("'").strip()
            return j.data.types.get("string", default=txt)

        if "." in txt:
            return j.data.types.get("float", default=txt)

        if "true" in txt.lower() or "false" in txt.lower():
            return j.data.types.get("bool", default=txt)

        if "[]" in txt:
            return j.data.types.get("ls", default=txt)

        if j.data.types.int.checkString(txt):  # means is digit
            return j.data.types.get("i", default=txt)
        else:
            raise RuntimeError("cannot find type for:%s" % txt)

    def _schema_from_text(self, text):
        """
        get schema object from schema text
        """

        self._log_debug("load schema", data=text)

        if text.count("@url") > 1:
            raise j.exceptions.Input("there should only be 1 url in the schema")

        self.text = j.core.text.strip(text)

        systemprops = {}
        self.properties = []
        # self._systemprops = systemprops

        def process(line):
            def _getdefault(txt):
                if '"' in txt or "'" in txt:
                    txt = txt.strip().strip('"').strip("'").strip()
                if txt.strip() == "":
                    return None
                txt = txt.strip()
                return txt

            line_original = copy(line)
            propname, line = line.split("=", 1)
            propname = propname.strip()
            if ":" in propname:
                self._error_raise(
                    "Aliases no longer supported in names, remove  ':' in name '%s'" % propname, schema=text
                )
            line = line.strip()

            if "!" in line:
                line, pointer_type = line.split("!", 1)
                pointer_type = pointer_type.strip()
                line = line.strip()
            else:
                pointer_type = None

            if "#" in line:
                line, comment = line.split("#", 1)
                line = line.strip()
                comment = comment.strip()
            else:
                comment = ""

            p = SchemaProperty()

            name = propname + ""  # make sure there is copy
            if name.endswith("**"):
                name = name[:-2]
                p.index = True
            if name.endswith("*"):
                name = name[:-1]
                p.index_key = True
            if name.startswith("&"):
                name = name[1:]
                p.unique = True
                # everything which is unique also needs to be indexed
                p.index_key = True

            if name in ["id"]:
                self._error_raise("do not use 'id' in your schema, is reserved for system.", schema=text)

            if "(" in line:
                line_proptype = line.split("(")[1].split(")")[0].strip().lower()  # in between the ()
                self._log_debug("line:%s; lineproptype:'%s'" % (line_original, line_proptype))
                line_wo_proptype = line.split("(")[0].strip()  # before the (

                if pointer_type:
                    default = pointer_type
                    # means the default is a link to another object
                else:
                    # will make sure we convert the default to the right possible type int,float, string
                    default = _getdefault(line_wo_proptype)

                jumpscaletype = j.data.types.get(line_proptype, default=default)

                defvalue = None

            else:
                jumpscaletype = self._proptype_get(line)
                defvalue = None

            jumpscaletype._jsx_location

            p.name = name
            if defvalue:
                p._default = defvalue
            p.comment = comment
            p.jumpscaletype = jumpscaletype

            return p

        nr = 0
        for line in text.split("\n"):
            line = line.strip()
            self._log_debug("L:%s" % line)
            nr += 1
            if line.strip() == "":
                continue
            if line.startswith("@"):
                if "#" in line:
                    line, _ = line.split("#", 1)
                systemprop_name = line.split("=")[0].strip()[1:]
                systemprop_val = line.split("=")[1].strip()
                systemprops[systemprop_name] = systemprop_val.strip('"').strip("'")
                continue
            if line.startswith("#"):
                continue
            if "=" not in line:
                raise j.exceptions.Input(
                    "did not find =, need to be there to define field, line=%s\ntext:%s" % (line, text)
                )

            p = process(line)

            if p.jumpscaletype.NAME is "list":
                raise RuntimeError("no longer used")
                # j.shell()
                # print(p.capnp_schema)
                # self.lists.append(p)
            else:
                self.properties.append(p)

        for key, val in systemprops.items():
            if key == "url":
                if self.url:
                    assert self.url == val
                else:
                    self.url = val
            else:
                self.systemprops.__dict__[key] = val

        nr = 0
        for s in self.properties:
            s.nr = nr
            self.__dict__["property_%s" % s.name] = s
            nr += 1

    @property
    def _capnp_id(self):
        if self._md5 == "":
            raise RuntimeError("hash cannot be empty")
        return "f" + self._md5[1:16]  # first bit needs to be 1

    @property
    def _capnp_schema(self):
        if not self._capnp:
            self._capnp = j.data.capnp.getSchemaFromText(self._capnp_schema_text)
        return self._capnp

    @property
    def _capnp_schema_text(self):
        tpath = "%s/templates/schema.capnp" % self._path
        # j.shell()
        _capnp_schema_text = j.tools.jinja2.template_render(path=tpath, reload=False, obj=self, objForHash=self._md5)
        return _capnp_schema_text

    @property
    def objclass(self):
        if self._obj_class is None:

            if self._md5 in [None, ""]:
                raise RuntimeError("md5 cannot be None")

            for prop in self.properties:
                self._log_debug("prop for obj gen: %s:%s" % (prop, prop.js_typelocation))

            tpath = "%s/templates/template_obj.py" % self._path

            # lets do some tests to see if it will render well, jinja doesn't show errors propertly
            for prop in self.properties:
                prop.capnp_schema
                prop.default_as_python_code
                prop.js_typelocation

            self._obj_class = j.tools.jinja2.code_python_render(
                name="schema_%s" % self.key, obj_key="ModelOBJ", path=tpath, obj=self, objForHash=self._md5
            )

        return self._obj_class

    def get(self, data=None, model=None):
        """
        get schema_object using data and capnpbin
        :param data dict, bytes or json(dict)
        :param model: will make sure we save in the model
        :return:
        """
        if isinstance(data, bytes):
            return j.data.serializers.jsxdata.loads(data)
        return self._get(data=data, model=model)

    def _get(self, data=None, model=None):
        obj = self.objclass(schema=self, data=data, model=model)
        return obj

    def new(self, model=None, data=None):
        """
        data is dict or None
        """
        if isinstance(data, bytes):
            raise RuntimeError("when creating new obj from schema cannot give bytes as starting point, dict ok")
        r = self.get(data=data, model=model)
        if model is not None:
            model.notify_new(r)
        return r

    # @property
    # def propertynames_index_sql(self):
    #     """
    #     list of the property names which are used for indexing in sql db (sqlite)
    #     :return:
    #     """
    #     res=[]
    #     for prop in self.properties:
    #         if prop.index:
    #             res.append(prop.name)
    #     return res

    @property
    def properties_index_sql(self):
        """
        list of the properties which are used for indexing in sql db (sqlite)
        :return:
        """
        res = []
        for prop in self.properties:
            if prop.index:
                res.append(prop)
        return res

    @property
    def properties_index_keys(self):
        """
        list of the properties which are used for indexing with keys
        :return:
        """
        res = []
        for prop in self.properties:
            if prop.index_key:
                res.append(prop)
        return res

    @property
    def properties_unique(self):
        """
        list of the properties which are used for indexing with keys
        :return:
        """
        res = []
        for prop in self.properties:
            if prop.unique:
                res.append(prop)
        return res

    @property
    def propertynames(self):
        """
        lists all the property names
        :return:
        """
        res = [item.name for item in self.properties]
        return res

    def __str__(self):
        out = "## SCHEMA: %s\n\n" % self.url
        for item in self.properties:
            out += str(item) + "\n"
        out += str(self.systemprops)
        return out

    def __eq__(self, other):
        if other is None:
            return False
        return other._md5 == self._md5

    __repr__ = __str__
