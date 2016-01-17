import unittest

import gator.common as common
import gator.apiclient as apiclient
import gator.config as config

from gator.version import MigrationHandlers
from gator.models import Model, customers

class TestHandler():
    @staticmethod
    def forward(item):
        item["key"] = True

    @staticmethod
    def backward(item):
        del item["key"]

class TestCustomer(Model):
    VALID_KEYS = ["uuid", "key", "version"]
    TABLE = customers
    VERSION = 1
    KEY = "uuid"
    HANDLERS = MigrationHandlers(VERSION)
    HANDLERS.add_handler(0, TestHandler)

    def __init__(self, item):
        super().__init__(item)

    def create_new(attributes={}):
        attributes["uuid"] = "1"
        attributes["version"] = TestCustomer.VERSION
        attributes["key"] =  "2"

        return Model.load_from_data(TestCustomer, attributes)

    # Required by the model interface
    def isValid(self):
        return True

class TestMigration(unittest.TestCase):
    def setUp(self):
        apiclient.clear_database()

    def test_simple_migration(self):
        # Manually create a customer on the old version
        data = {
            "uuid": "1",
            "version": 0
        }

        customer = Model.load_from_data(TestCustomer, data)

        # Check to see that the item is at the new version
        self.assertEquals(customer["uuid"], "1")
        self.assertEquals(customer["version"], 1)
        self.assertEquals(customer["key"], True)

        # Get the data and make sure its on the old version
        retreived_data = customer.get_data(version=0)
        self.assertEquals(retreived_data["uuid"], "1")
        self.assertEquals(retreived_data["version"], 0)
        self.assertIsNone(retreived_data.get("key"))

    def test_migration_load_from_db(self):
        data = {
            "uuid": "1",
            "version": 0
        }

        # Manually put the item into the database
        customers.put_item(data)

        # Load the item from the db and check to see that it
        # is on the latest version
        customer = Model.load_from_db(TestCustomer, "1")
        self.assertEquals(customer["uuid"], "1")
        self.assertEquals(customer["version"], 1)
        self.assertEquals(customer["key"], True)

        # Check to make sure that the db has been updated to
        # the latest version
        db_item = customers.get_item(consistent=True, **{"uuid": "1"})
        self.assertEquals(db_item["uuid"], "1")
        self.assertEquals(db_item["version"], 1)
        self.assertEquals(db_item["key"], True)
