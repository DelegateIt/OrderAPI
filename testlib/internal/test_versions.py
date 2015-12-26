import unittest
from copy import deepcopy

import gator.version as version

from gator.version import MigrationHandlers
from gator.common import GatorException

# Test handlers used to mock a real migration
class TestHandler1():
    @staticmethod
    def forward(item):
        item["test1"] = True

    @staticmethod
    def backward(item):
        pass

class TestHandler2():
    @staticmethod
    def forward(item):
        item["test2"] = item["test1"]
        del item["test1"]

    @staticmethod
    def backward(item):
        item["test1"] = item["test2"]
        del item["test2"]


class TestVersion(unittest.TestCase):
    def setUp(self):
        self.handlers = MigrationHandlers(2)
        self.handlers.add_handler(0, TestHandler1)
        self.handlers.add_handler(1, TestHandler2)

    def test_forward_migration(self):
        item = {"version": 1, "test1": True}
        self.handlers.migrate_forward_item(item)

        self.assertEquals(item["version"], 2)
        self.assertEquals(item["test2"], True)
        self.assertIsNone(item.get("test1"))

    def test_backward_migration(self):
        item = {"version": 2, "test2": False}
        self.handlers.migrate_backward_item(item, 1)

        self.assertEquals(item["version"], 1)
        self.assertEquals(item["test1"], False)
        self.assertIsNone(item.get("test2"))

    def test_double_forward_migration(self):
        item = {"version": 0}
        self.handlers.migrate_forward_item(item)

        self.assertEquals(item["version"], 2)
        self.assertEquals(item["test2"], True)
        self.assertIsNone(item.get("test1"))

    def test_double_backward_migration(self):
        item = {"version": 2, "test2": True}
        self.handlers.migrate_backward_item(item, 0)

        self.assertEquals(item["version"], 0)
        self.assertEquals(item["test1"], True)
        self.assertIsNone(item.get("test2"))

    def test_unnecessary_migration(self):
        item = {"version": 2}
        orig_item = deepcopy(item)

        self.handlers.migrate_forward_item(item)
        self.assertEquals(item, orig_item)

        self.handlers.migrate_backward_item(item, 2)
        self.assertEquals(item, orig_item)

    def test_unsuported_version_forward_migration(self):
        item = {"version": 3}

        with self.assertRaises(GatorException):
            self.handlers.migrate_forward_item(item)

    def test_unsuported_version_backward_migration(self):
        item = {"version": 2}

        with self.assertRaises(ValueError):
            self.handlers.migrate_backward_item(item, 3)

        with self.assertRaises(GatorException):
            self.handlers.migrate_backward_item(item, -1)

    def test_add_duplicate_handler(self):
        with self.assertRaises(ValueError):
            self.handlers.add_handler(0, None)

class TestCurrentHandlers(unittest.TestCase):
    def test_version_handler(self):
        handlers = MigrationHandlers(1)
        handlers.add_handler(0, version.VersionHandler)
        item = {"version": 0}

        handlers.migrate_forward_item(item)
        self.assertEquals(item["version"], 1)

        handlers.migrate_backward_item(item, 0)
        self.assertEquals(item["version"], 0)
