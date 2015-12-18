from boto.dynamodb2.table import Table, Item
from boto.dynamodb2.exceptions import ConditionalCheckFailedException, ItemNotFound

import jsonpickle

import time
import json
import uuid
from enum import Enum, unique

import gator.service as service
import gator.common as common
import gator.config as config

from gator.common import TransactionStates, Platforms

##############################
# Global vars, consts, extra #
##############################

conn = service.dynamodb

# Class of table names
class TableNames():
    CUSTOMERS    = "DelegateIt_Customers"
    DELEGATORS   = "DelegateIt_Delegators"
    TRANSACTIONS = "DelegateIt_Transactions"
    HANDLERS     = "DelegateIt_Handlers"

# Tables
table_prefix = config.store["dynamodb"]["table_prefix"]
customers    = Table(table_prefix + TableNames.CUSTOMERS,    connection=conn)
delegators   = Table(table_prefix + TableNames.DELEGATORS,   connection=conn)
transactions = Table(table_prefix + TableNames.TRANSACTIONS, connection=conn)
handlers     = Table(table_prefix + TableNames.HANDLERS,     connection=conn)

# Use boolean for the tables
customers.use_boolean()
delegators.use_boolean()
transactions.use_boolean()
handlers.use_boolean()

SCHEMA_VERSION_KEY = "schema_version"

# Base class for all object models
class Model():
    def __init__(self, item):
        if not self._atts_are_valid(item._data):
            #TODO change this to a GatorException
            raise ValueError("One or more of the item's attributes is invalid")

        self.item = item

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
            item = cls(cls.TABLE.get_item(
                consistent=consistent,
                **{
                    cls.KEY: key
                }))
        except ItemNotFound:
            pass

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
        return key in self.item

    def update(self, atts):
        for key, val in atts.items():
            self[key] = val

    def _atts_are_valid(self, attributes):
        # Verify that the attributes passed in were valid
        for atr in attributes:
            if atr not in self.VALID_KEYS:
                return False

        return True

    def get_data(self):
        return self.item._data

    # Database Logic
    def save(self):
        # Defauult dynamodb behavior returns false if no save was performed
        if not self.item.needs_save():
            return True

        try:
            return self.item.partial_save()
        except ConditionalCheckFailedException:
            return False

    def create(self):
        if self.is_unique():
            return self.item.save()
        else:
            return False

    def delete(self):
        return self.item.delete()

    # Parsing and json
    def to_json(self):
        return jsonpickle.encode(get_data())

class TCFields():
    A_TRANS_UUIDS = "active_transaction_uuids"
    IA_TRANS_UUIDS = "inactive_transaction_uuids"

class TransactionContainerFunctions():
    @staticmethod
    def add_transaction(obj, transaction):
        if transaction[TFields.UUID] is None or transaction[TFields.STATUS] is None:
            raise ValueError("Transaction must have UUID and STATUS fields")

        is_active = transaction[TFields.STATUS] in TransactionStates.ACTIVE_STATES
        trans_type = TCFields.A_TRANS_UUIDS if is_active else TCFields.IA_TRANS_UUIDS

        if obj.item[trans_type] is None:
            obj.item[trans_type] = []

        obj.item[trans_type].append(transaction[TFields.UUID])

    @staticmethod
    def update_transaction_status(obj, transaction):
        if transaction[TFields.UUID] is None or transaction[TFields.STATUS] is None:
            raise ValueError("Transaction must have UUID and STATUS fields")

        old_is_active = transaction[TFields.UUID] in obj[TCFields.A_TRANS_UUIDS]
        new_is_active = transaction[TFields.STATUS] in TransactionStates.ACTIVE_STATES

        if old_is_active == (not new_is_active):
            old_trans_type = TCFields.A_TRANS_UUIDS if old_is_active else TCFields.IA_TRANS_UUIDS
            new_trans_type = TCFields.A_TRANS_UUIDS if new_is_active else TCFields.IA_TRANS_UUIDS

            obj[old_trans_type].remove(transaction[TFields.UUID])

            if obj[new_trans_type] is None:
                obj[new_trans_type] = []

            obj[new_trans_type].append(transaction[TFields.UUID])

    @staticmethod
    def remove_transaction(obj, transaction):
        if transaction[TFields.UUID] is None or transaction[TFields.STATUS] is None:
            raise ValueError("Transaction must have UUID and STATUS fields")

        is_active = transaction[TFields.STATUS] in TransactionStates.ACTIVE_STATES
        trans_type = TCFields.A_TRANS_UUIDS if is_active else TCFields.IA_TRANS_UUIDS

        obj.item[trans_type].remove(transaction[TFields.UUID])

class CFields():
    UUID = "uuid"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FBUSER_ID = "fbuser_id"
    STRIPE_ID = "stripe_id"
    A_TRANS_UUIDS = TCFields.A_TRANS_UUIDS
    IA_TRANS_UUIDS = TCFields.IA_TRANS_UUIDS
    SCHEMA_VERSION = SCHEMA_VERSION_KEY

class Customer(Model):
    FIELDS = CFields
    VALID_KEYS = set([getattr(CFields, attr) for attr in vars(CFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.CUSTOMERS
    TABLE = customers
    KEY = CFields.UUID
    # TODO Do we still want phone number to mandatory for app users?
    MANDATORY_KEYS = set([CFields.PHONE_NUMBER]) # TODO remove this later

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        customer = Model.load_from_data(Customer, attributes)

        # Default values
        customer[CFields.UUID] = common.get_uuid()

        return customer

    def is_unique(self):
        if not self.MANDATORY_KEYS <= set(self.get_data()):
            return False
        if self["fbuser_id"] is not None and customers.query_count(index="fbuser_id-index", fbuser_id__eq=self["fbuser_id"]) != 0:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self["phone_number"]) == 0

    # Utility Methods
    def add_transaction(self, transaction):
        TransactionContainerFunctions.add_transaction(self, transaction)

    def update_transaction_status(self, transaction):
        TransactionContainerFunctions.update_transaction_status(self, transaction)

class DFields():
    UUID = "uuid"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FBUSER_ID = "fbuser_id"
    A_TRANS_UUIDS = TCFields.A_TRANS_UUIDS
    IA_TRANS_UUIDS = TCFields.IA_TRANS_UUIDS
    SCHEMA_VERSION = SCHEMA_VERSION_KEY

class Delegator(Model):
    FIELDS = DFields
    VALID_KEYS = set([getattr(DFields, attr) for attr in vars(DFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.DELEGATORS
    TABLE = delegators
    KEY = DFields.UUID
    MANDATORY_KEYS = set([DFields.FBUSER_ID, DFields.PHONE_NUMBER, DFields.EMAIL, DFields.FIRST_NAME, DFields.LAST_NAME])

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        delegator = Model.load_from_data(Delegator, attributes)

        # Default values
        delegator[DFields.UUID] = common.get_uuid()

        return delegator

    def is_unique(self):
        if not self.MANDATORY_KEYS <= set(self.get_data()):
            return False

        phone_number_is_uniq = delegators.query_count(index="phone_number-index", phone_number__eq=self[DFields.PHONE_NUMBER], limit=1) == 0
        email_is_uniq = delegators.query_count(index="email-index", email__eq=self[DFields.EMAIL], limit=1) == 0
        fbuser_id_is_uniq    = delegators.query_count(index="fbuser_id-index", fbuser_id__eq=self["fbuser_id"], limit=1) == 0

        return phone_number_is_uniq and email_is_uniq and fbuser_id_is_uniq

    # Utility Methods
    def add_transaction(self, transaction):
        TransactionContainerFunctions.add_transaction(self, transaction)

    def remove_transaction(self, transaction):
        TransactionContainerFunctions.remove_transaction(self, transaction)

    def update_transaction_status(self, transaction):
        TransactionContainerFunctions.update_transaction_status(self, transaction)

class TFields():
    UUID = "uuid"
    CUSTOMER_UUID = "customer_uuid"
    DELEGATOR_UUID = "delegator_uuid"
    STATUS = "status"
    TIMESTAMP = "timestamp"
    MESSAGES = "messages"
    RECEIPT = "receipt"
    PAYMENT_URL = "payment_url"
    CUSTOMER_PLATFORM_TYPE = "customer_platform_type"
    SCHEMA_VERSION = SCHEMA_VERSION_KEY

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
    KEY = TFields.UUID
    MANDATORY_KEYS = set([TFields.CUSTOMER_UUID, TFields.CUSTOMER_PLATFORM_TYPE])

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        transaction = Model.load_from_data(Transaction, attributes)
        transaction[TFields.UUID] = common.get_uuid()
        transaction[TFields.TIMESTAMP] = common.get_current_timestamp()

        if transaction[TFields.STATUS] is None:
            transaction[TFields.STATUS] = TransactionStates.STARTED

        return transaction

    # Overriden Methods
    def is_unique(self):
        data = self.get_data()
        if not set(data) >= self.MANDATORY_KEYS:
            return False

        # Check to see if of the customers transactions are SMS
        if data[TFields.CUSTOMER_PLATFORM_TYPE] == Platforms.SMS:
            customer = Model.load_from_db(Customer, data[TFields.CUSTOMER_UUID])

            # Short circuit if the customer doesn't have any transactions
            # NOTE: ignores the current transaction if it exists in the customer
            if customer[CFields.A_TRANS_UUIDS] is not None:
                transaction_list = [Model.load_from_db(Transaction, transaction_uuid)
                        for transaction_uuid in customer[CFields.A_TRANS_UUIDS]
                        if transaction_uuid != data[TFields.UUID]]

                if any([transaction[TFields.CUSTOMER_PLATFORM_TYPE] == Platforms.SMS
                        for transaction in transaction_list]):
                    return False

        return True

    # Utility Methods
    def add_message(self, message):
        if self.item[TFields.MESSAGES] is None:
            self.item[TFields.MESSAGES] = []

        self.item[TFields.MESSAGES].append(message.get_data())

class MFields():
    FROM_CUSTOMER = "from_customer"
    CONTENT = "content"
    TIMESTAMP = "timestamp"

class Message():
    def __init__(self, from_customer=None, content=None):
        setattr(self, MFields.FROM_CUSTOMER, from_customer)
        setattr(self, MFields.CONTENT, content)
        setattr(self, MFields.TIMESTAMP, common.get_current_timestamp())

    def get_timestamp(self):
        return getattr(self, MFields.TIMESTAMP)

    def get_data(self):
        return {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}
