from boto.dynamodb2.table import Table, Item
from boto.dynamodb2.exceptions import ConditionalCheckFailedException

import jsonpickle

import time
import json
import uuid
from enum import Enum, unique

from gator import service
from gator import common

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
customers    = Table(TableNames.CUSTOMERS,    connection=conn)
delegators   = Table(TableNames.DELEGATORS,   connection=conn)
transactions = Table(TableNames.TRANSACTIONS, connection=conn)
handlers     = Table(TableNames.HANDLERS,     connection=conn)

# Base class for all object models
class Model():
    def __init__(self, item):
        if not self._atts_are_valid(item._data):
            raise ValueError("One or more of the item's attributes is invalid")

        self.item = item

    # Factory methods
    @staticmethod
    def load_from_db(cls, key, consistent=True):
        if not issubclass(cls, Model):
            raise ValueError("Class must be a subclass of Model")

        return cls(cls.TABLE.get_item(
            consistent=consistent,
            **{
                cls.KEY: key
            }))

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
        try:
            return self.item.partial_save()
        except ConditionalCheckFailedException:
            return False

    def create(self):
        return self.item.save()

    # Parsing and json
    def to_json(self):
        return jsonpickle.encode(get_data())

class CFields():
    UUID = "uuid"
    PHONE_NUMBER = "phone_number"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    STRIPE_ID = "stripe_id"
    A_TRANS_UUIDS = "active_transaction_uuids"
    IA_TRANS_UUIDS = "inactive_transaction_uuids" 

class Customer(Model):
    FIELDS = CFields
    VALID_KEYS = set([getattr(CFields, attr) for attr in vars(CFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.CUSTOMERS
    TABLE = customers
    KEY = CFields.UUID

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        customer = Model.load_from_data(Customer, attributes)

        # Default values
        customer[CFields.UUID] = common.get_uuid()

        if customer[CFields.A_TRANS_UUIDS] is None:
            customer[CFields.A_TRANS_UUIDS] = []

        if customer[CFields.IA_TRANS_UUIDS] is None:
            customer[CFields.IA_TRANS_UUIDS] = []

        return customer

    def is_unique(self):
        if self[CFields.PHONE_NUMBER] is None:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self["phone_number"]) == 0

    def create(self):
        if self.is_unique():
            return self.item.save()
        else:
            return False

class DFields():
    UUID = "uuid"
    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    A_TRANS_UUIDS = "active_transaction_uuids"
    IA_TRANS_UUIDS = "inactive_transaction_uuids" 

class Delegator(Model):
    FIELDS = DFields
    VALID_KEYS = set([getattr(DFields, attr) for attr in vars(DFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.DELEGATORS
    TABLE = delegators
    KEY = DFields.UUID

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        delegator = Model.load_from_data(Delegator, attributes)

        # Default values
        delegator[DFields.UUID] = common.get_uuid()

        if delegator[DFields.A_TRANS_UUIDS] is None:
            delegator[DFields.A_TRANS_UUIDS] = []

        if delegator[DFields.IA_TRANS_UUIDS] is None:
            delegator[DFields.IA_TRANS_UUIDS] = []

        return delegator

    def is_unique(self):
        if self[DFields.PHONE_NUMBER] is None or self[DFields.EMAIL] is None:
            return False

        phone_number_is_uniq = delegators.query_count(index="phone_number-index", phone_number__eq=self[DFields.PHONE_NUMBER]) == 0
        email_is_uniq = delegators.query_count(index="email-index", email__eq=self[DFields.EMAIL]) == 0

        return phone_number_is_uniq and email_is_uniq

    def create(self):
        if self.is_unique():
            return self.item.save()
        else:
            return False

class TFields():
    CUSTOMER_UUID = "customer_uuid"
    DELEGATOR_UUID = "delegator_uuid"
    STATUS = "status"
    MESSAGES = "messages"

class Transaction(Model):
    FIELDS = TFields
    VALID_KEYS = set([getattr(TFields, attr) for attr in vars(TFields)
        if not attr.startswith("__")])
    TABLE_NAME = TableNames.TRANSACTIONS
    TABLE = transactions
    KEY = TFields.CUSTOMER_UUID

    def __init__(self, item):
        super().__init__(item)

    @staticmethod
    def create_new(attributes={}):
        transaction = Model.load_from_data(Transaction, attributes)

        if transaction[TFields.STATUS] is None:
            transaction[TFields.STATUS] = common.TransactionStates.STARTED

        return transaction 

    def get_data(self):
        data = deepcopy(self.item._data)

        if data.get("messages") is not None:
            data["messages"] = [message.get_data() for message in data["messages"]]

        return data

    def add_message(message):
        if self.item[TFields.MESSAGES] == None:
            self.item[TFields.MESSAGES] = []

        self.item[TFields.MESSAGES].append(message.get_data())

class MFields():
    FROM_CUSTOMER = "from_customer"
    CONTENT = "content"
    PLATFORM_TYPE = "platform_type"
    TIMESTAMP = "timestamp"

class Message():
    def __init__(self, from_customer=None, content=None, platform_type=None):
        setattr(self, MFields.FROM_CUSTOMER, from_customer)
        setattr(self, MFields.CONTENT, content)
        setattr(self, MFields.PLATFORM_TYPE, platform_type)
        setattr(self, MFields.TIMESTAMP, common.get_current_timestamp())

    def get_data(self):
        return {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}
