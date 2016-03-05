import unittest

import gator.apiclient as apiclient
import gator.config as config
import gator.core.common as common

from gator.core.version import MigrationHandlers
from gator.core.models import Model, customers
from gator.core.common import GatorException

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

    @staticmethod
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

    """
        The following test is an example of what can happen during a rolling
        deployment when a new version is introduced and the database contains
        items on version N + 1 and current API node only supports up to version
        N
    """
    def test_invalid_migration(self):
        data = {
            "uuid": "1",
            "version": 2
        }

        # Manually put the item into the database
        customers.put_item(data)

        with self.assertRaises(GatorException) as e:
            customer = Model.load_from_db(TestCustomer, "1")

        try:
            Model.load_from_db(TestCustomer, "1")
            self.assertTrue(False) # Should never reach this point
        except GatorException as e:
            self.assertEquals(e.error_type.returncode, 23)
