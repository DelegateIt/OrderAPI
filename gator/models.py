from boto.dynamodb2.table import Table, Item
from boto.dynamodb2.exceptions import ConditionalCheckFailedException, ItemNotFound
from copy import deepcopy

import jsonpickle

import time
import json
import uuid
from enum import Enum, unique

import gator.service as service
import gator.common as common
import gator.config as config
import gator.version as version

from gator.common import TransactionStates, Platforms, Errors, GatorException
from gator.version import MigrationHandlers

##############################
# Global vars, consts, extra #
##############################

conn = service.dynamodb

# Class of table names
table_prefix = config.store["dynamodb"]["table_prefix"]
class TableNames():
    CUSTOMERS    = table_prefix + "DelegateIt_Customers"
    DELEGATORS   = table_prefix + "DelegateIt_Delegators"
    TRANSACTIONS = table_prefix + "DelegateIt_Transactions_CD"
    HANDLERS     = table_prefix + "DelegateIt_Handlers"

# Tables
customers    = Table(TableNames.CUSTOMERS,    connection=conn)
delegators   = Table(TableNames.DELEGATORS,   connection=conn)
transactions = Table(TableNames.TRANSACTIONS, connection=conn)
handlers     = Table(TableNames.HANDLERS,     connection=conn)

# Use boolean for the tables
customers.use_boolean()
delegators.use_boolean()
transactions.use_boolean()
handlers.use_boolean()

# Base class for all object models
class Model():
    def __init__(self, item):
        if not self._atts_are_valid(item._data):
            raise GatorException(Errors.INVALID_DATA_PRESENT)

        self.item = item
        self.HANDLERS.migrate_forward_item(item)

    # Factory methods
    @staticmethod
    def load_from_db(cls, key, consistent=True):
        if not issubclass(cls, Model):
            raise ValueError("Class must be a subclass of Model")

        # None keys cause dynamodb exception
        if key is None:
            return None

        item = None
        try:
            full_key = { }
            if key.find("-") == -1:
                full_key[cls.KEY] = key
            else:
                split = key.split("-", 2)
                full_key[cls.KEY] = split[0]
                full_key[cls.RANGE_KEY] = int(split[1])

            item = cls(cls.TABLE.get_item(consistent=consistent, **full_key))

            # Migrate the item forward if it is on an old version
            if item["version"] <= cls.VERSION:
                cls.HANDLERS.migrate_forward_item(item)
                if not item.save():
                    return None
        except ItemNotFound:
            raise GatorException(cls.ITEM_NOT_FOUND_EX)

        return item

    @staticmethod
    def load_from_data(cls, data):
        if not issubclass(cls, Model):
            raise ValueError("Class must be a subclass of Model")

        return cls(Item(cls.TABLE, data))

    # Attribute access
    def __getitem__(self, key):
        return self.item[key]

    def __setitem__(self, key, val):
        if key in self.VALID_KEYS:
            self.item[key] = val
        else:
            raise ValueError("Attribute %s is not valid." % key)

    def __contains__(self, key):
        return key in self.get_data()

    def update(self, atts):
        for key, val in atts.items():
            self[key] = val

    def _atts_are_valid(self, attributes):
        # Verify that the attributes passed in were valid
        for atr in attributes:
            if atr not in self.VALID_KEYS:
                return False

        return True

    def get_data(self, version=None):
        # Default to the latest version
        new_version = version if version is not None else self.VERSION

        self.HANDLERS.migrate_backward_item(self.item, new_version)
        data = deepcopy(self.item._data)
        self.HANDLERS.migrate_forward_item(self.item)

        return data

    # Database Logic
    def save(self):
        # Defauult dynamodb behavior returns false if no save was performed
        if not self.item.needs_save():
            return True
        # Don't allow empty keys to be saved
        elif any([val == "" for val in self.get_data().values()]):
            raise GatorException(Errors.INVALID_DATA_PRESENT)

        try:
            return self.item.partial_save()
        except ConditionalCheckFailedException:
            return False

    def create(self):
        # Don't allow empty keys to be saved
        if any([val == "" for val in self.get_data().values()]):
            raise GatorException(Errors.INVALID_DATA_PRESENT)

        if self.is_valid():
            return self.item.save()
        else:
            return False

    def delete(self):
        return self.item.delete()

class CFields():
    UUID = "uuid"
    VERSION = "version"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FBUSER_ID = "fbuser_id"
    STRIPE_ID = "stripe_id"

class Customer(Model):
    FIELDS = CFields
    VALID_KEYS = set([getattr(CFields, attr) for attr in vars(CFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.CUSTOMERS
    TABLE = customers
    KEY = CFields.UUID
    MANDATORY_KEYS = set([])
    VERSION = 1
    ITEM_NOT_FOUND_EX = Errors.CUSTOMER_DOES_NOT_EXIST

    # Initialize the migration handlers
    HANDLERS = MigrationHandlers(VERSION)
    HANDLERS.add_handler(0, version.VersionHandler)

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        # Default Values
        attributes[CFields.UUID] = common.get_uuid()
        attributes[CFields.VERSION] = Customer.VERSION

        return Model.load_from_data(Customer, attributes)

    def is_valid(self):
        if not self.MANDATORY_KEYS <= set(self.get_data()):
            return False
        if self["fbuser_id"] is not None and customers.query_count(index="fbuser_id-index", fbuser_id__eq=self["fbuser_id"]) != 0:
            return False

        return (self["phone_number"] is None or
                customers.query_count(index="phone_number-index", phone_number__eq=self["phone_number"]) == 0)

class DFields():
    UUID = "uuid"
    VERSION = "version"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FBUSER_ID = "fbuser_id"

class Delegator(Model):
    FIELDS = DFields
    VALID_KEYS = set([getattr(DFields, attr) for attr in vars(DFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.DELEGATORS
    TABLE = delegators
    KEY = DFields.UUID
    MANDATORY_KEYS = set([DFields.FBUSER_ID, DFields.PHONE_NUMBER, DFields.EMAIL, DFields.FIRST_NAME, DFields.LAST_NAME])
    VERSION = 1
    ITEM_NOT_FOUND_EX = Errors.DELEGATOR_DOES_NOT_EXIST

    # Initialize the migration handlers
    HANDLERS = MigrationHandlers(VERSION)
    HANDLERS.add_handler(0, version.VersionHandler)

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        # Default Values
        attributes[DFields.UUID] = common.get_uuid()
        attributes[DFields.VERSION] = Delegator.VERSION

        return Model.load_from_data(Delegator, attributes)

    def is_valid(self):
        if not self.MANDATORY_KEYS <= set(self.get_data()):
            return False

        phone_number_is_uniq = delegators.query_count(index="phone_number-index", phone_number__eq=self[DFields.PHONE_NUMBER], limit=1) == 0
        email_is_uniq = delegators.query_count(index="email-index", email__eq=self[DFields.EMAIL], limit=1) == 0
        fbuser_id_is_uniq    = delegators.query_count(index="fbuser_id-index", fbuser_id__eq=self["fbuser_id"], limit=1) == 0

        return phone_number_is_uniq and email_is_uniq and fbuser_id_is_uniq

class TFields():
    UUID = "uuid"
    VERSION = "version"
    CUSTOMER_UUID = "customer_uuid"
    DELEGATOR_UUID = "delegator_uuid"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    MESSAGES = "messages"
    RECEIPT = "receipt"
    PAYMENT_URL = "payment_url"
    CUSTOMER_PLATFORM_TYPE = "customer_platform_type"

class RFields():
    ITEMS = "items"
    STRIPE_CHARGE_ID = "stripe_charge_id"
    TOTAL = "total"
    NOTES = "notes"

class Transaction(Model):
    FIELDS = TFields
    VALID_KEYS = set([getattr(TFields, attr) for attr in vars(TFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.TRANSACTIONS
    TABLE = transactions
    KEY = TFields.CUSTOMER_UUID
    RANGE_KEY = TFields.TIMESTAMP
    MANDATORY_KEYS = set([TFields.CUSTOMER_UUID, TFields.CUSTOMER_PLATFORM_TYPE])
    VERSION = 3
    ITEM_NOT_FOUND_EX = Errors.TRANSACTION_DOES_NOT_EXIST

    # Initialize the migration handlers
    HANDLERS = MigrationHandlers(VERSION)
    HANDLERS.add_handler(0, version.VersionHandler)
    HANDLERS.add_handler(1, version.MigratePlatformType)
    HANDLERS.add_handler(2, version.AddMessageType)

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        # Default Values
        attributes[TFields.VERSION] = Transaction.VERSION
        attributes[TFields.TIMESTAMP] = common.get_current_timestamp()
        attributes[TFields.UUID] = (attributes[TFields.CUSTOMER_UUID] + "-" +
                str(attributes[TFields.TIMESTAMP]))

        if attributes.get(TFields.STATUS) is None:
            attributes[TFields.STATUS] = TransactionStates.STARTED

        return Model.load_from_data(Transaction, attributes)

    # Overriden Methods
    def is_valid(self):
        data = self.get_data()
        if not set(data) >= self.MANDATORY_KEYS:
            return False
        return True

    # Utility Methods
    def add_message(self, message):
        if self.item[TFields.MESSAGES] is None:
            self.item[TFields.MESSAGES] = []

        self.item[TFields.MESSAGES].append(message.get_data())

class MTypes():
    TEXT = "text"
    RECEIPT = "receipt"
    IMAGE = "image"

class MFields():
    FROM_CUSTOMER = "from_customer"
    CONTENT = "content"
    TIMESTAMP = "timestamp"
    MTYPE = "type"

class Message():
    VALID_MESSAGE_TYPES = set([getattr(MTypes, attr) for attr in vars(MTypes)
            if not attr.startswith("__")])

    def __init__(self, from_customer=None, content=None, mtype=None):
        setattr(self, MFields.FROM_CUSTOMER, from_customer)
        setattr(self, MFields.CONTENT, content)
        setattr(self, MFields.MTYPE, mtype)
        setattr(self, MFields.TIMESTAMP, common.get_current_timestamp())
        if mtype is not None and mtype not in self.VALID_MESSAGE_TYPES:
            raise GatorException(Errors.INVALID_MSG_TYPE)

    def get_timestamp(self):
        return getattr(self, MFields.TIMESTAMP)

    def get_data(self):
        return {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}
