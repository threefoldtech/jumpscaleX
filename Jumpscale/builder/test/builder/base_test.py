from Jumpscale import j
from unittest import TestCase
from unittest.mock import MagicMock


class BaseTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setUp(self):
        self.builder = j.builder.system.dummy

    def tearDown(self):
        self.builder._done_reset()

    def test_init_before_methods(self):
        self.builder.build()
        assert hasattr(self.builder, "variable")
        assert self.builder.variable == "value"

    def test_reset(self):
        assert self.builder.build() is None
        assert self.builder.build() == self.builder.ALREADY_DONE_VALUE
        assert self.builder.build(reset=True) is None
        assert self.builder.build() == self.builder.ALREADY_DONE_VALUE

    def test_dependencies(self):
        assert self.builder.sandbox() is None
        assert self.builder.install() == self.builder.ALREADY_DONE_VALUE
        assert self.builder.build() == self.builder.ALREADY_DONE_VALUE

    def test_kwargs_as_args(self):
        assert self.builder.sandbox(None) is None
        assert self.builder.sandbox(zhub_client=None) == self.builder.ALREADY_DONE_VALUE

    def test_sandbox(self):
        self.builder._flist_create = MagicMock()
        zhub_client = j.clients.zhub.testinstance
        assert self.builder.sandbox(zhub_client) is None
        self.builder._flist_create.assert_not_called()
        assert self.builder.sandbox(zhub_client, flist_create=True)
        self.builder._flist_create.assert_called()


