from Jumpscale import j
from .JSBaseDataObj import JSBaseDataObj


class JSBaseConfig(JSBaseDataObj):
    def __init__(self, data=None, parent=None, topclass=True, **kwargs):
        """
        :param data, is a jsobject as result of jsX schema's
        :param factory, don't forget to specify this
        :param kwargs: will be updated in the self.data object

        the self.data object is a jsobject (result of using the jsx schemas)

        """

        JSBaseDataObj.__init__(self, data=data, parent=parent, topclass=False, **kwargs)

        self._isnew = False

        if parent not in [None, ""]:
            self._model = self._parent._model
        else:
            self._model = j.application.bcdb_system.model_get_from_schema(self.__class__._SCHEMATEXT)
            self._init_pre(**kwargs)
            self._init()

        self._model._kosmosinstance = self

        if "name" not in self.data._ddict:
            raise RuntimeError("name needs to be specified in data")

        if topclass:
            self._init_pre(**kwargs)
            self._init()

    def delete(self):
        self._model.delete(self.data)
        if self._parent:
            if self.data.name in self._parent._children:
                del self._parent._children[self.data.name]

    def save(self):
        self.data.save()

    def _properties_model(self):
        return self._model.schema.propertynames
