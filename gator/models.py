from boto.dynamodb2.table import Table
from boto.dynamodb2.layer1 import DynamoDBConnection

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
    # Generic super initializer
    def __init__(self):
        self.dirty_keys = set([])

    # Decorators
    def mark_dirty(func):
        def wrapper(self, key, val):
            self.dirty_keys.add(key)
            
            return func(self, key, val)

        return wrapper

    # Attribute access
    def __getitem__(self, key):
        return getattr(self, key, None)

    @mark_dirty
    def __setitem__(self, key, val):
        if key in self.VALID_KEYS:
            setattr(self, key, val)
        else:
            raise ValueError("Attribute %s is not valid." % key)

    def get_dirty_keys(self):
        return self.dirty_keys

    def get_data(self):
        return {key: vars(self)[key] for key in vars(self)
                if vars(self)[key] is not None and key in self.VALID_KEYS}

    # Database Logic
    def save(self):
        data=self.get_data()

        # TODO : fix this later
        if data.get(self.FIELDS.VERSION) is None:
            raise ValueError("Model object must have a version to be used with save.")

        result = self.TABLE.put_item(data={key: data[key] for key in self.dirty_keys})
        # Reset the dirty keys
        self.dirty_keys = self.dirty_keys if result else set([])

        return result

    def create(self):
        return self.TABLE.put_item(data=self.get_data())

    # Parsing and json
    def to_json(self):
        return jsonpickle.encode(get_data())

class CFields():
    UUID = "uuid"
    VERSION = "version"
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
    
    # NOTE : does not require use of a primary key
    def __init__(self, attributes):
        # Call super class init
        super(Customer, self).__init__()
        
        for atr, val in attributes.items():
            if atr in self.VALID_KEYS:
                self[atr] = val
            else:
                raise ValueError("Attribute %s is not valid." % (atr))

    @staticmethod
    def create_new(attributes):
        customer = Customer(attributes)

        # Default values
        customer[CFields.UUID] = common.get_uuid()

        if customer[CFields.A_TRANS_UUIDS] is None:
            customer[CFields.A_TRANS_UUIDS] = []

        if customer[CFields.IA_TRANS_UUIDS] is None:
            customer[CFields.IA_TRANS_UUIDS] = []

        return customer

    @staticmethod
    def load_from_db(uuid, consistent=True):
        return Customer(TABLE.get_item(uuid=uuid, consistent=consistent)._data)

    def is_unique(self):
        if self[CFields.PHONE_NUMBER] is None:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self["phone_number"]) == 0

class Delegator():
    def __init__(self, phone_number=None, email=None, first_name=None, last_name=None,
            active_transaction_uuids=None, inactive_transaction_uuids=None):
        self.uuid = common.get_uuid()
        self.phone_number = phone_number
        self.email = email
        self.first_name   = first_name
        self.last_name    = last_name

        self.active_transaction_uuids = active_transaction_uuids
        self.inactive_transaction_uuids = inactive_transaction_uuids

    def get_data(self):
        data = {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}

        if data.get("active_transaction_uuids") is not None:
            data["active_transaction_uuids"] = [transaction.get_data() for transaction in data["active_transaction_uuids"]]

        if data.get("inactive_transaction_uuids") is not None:
            data["inactive_transaction_uuids"] = [transaction.get_data() for transaction in data["inactive_transaction_uuids"]]

        return data

    def is_unique(self):
        if self.phone_number is None or self.email is None:
            return False

        phone_number_is_uniq = delegators.query_count(index="phone_number-index", phone_number__eq=self.phone_number) == 0
        email_is_uniq        = delegators.query_count(index="email-index", email__eq=self.email) == 0

        return phone_number_is_uniq and email_is_uniq

class Transaction():
    def __init__(self, customer_uuid=None, delegator_uuid=None, status=None, messages=None):
        self.uuid = common.get_uuid()
        self.customer_uuid = customer_uuid
        self.delegator_uuid = delegator_uuid
        self.status = status
        self.timestamp = common.get_current_timestamp()
        self.messages = messages
        self.receipt = None
        self.payment_url = None

        # RECEIPT STRUCTURE
        # receipt = {
        #     total: integer, #Amount of cents that should be paid. NOTE: not equal to the sum of costs due to fees/taxes
        #     paid: boolean,
        #     notes: string, #Any additional information
        #     items: [
        #         {
        #             name: string,
        #             cents: int #cost of item in pennies
        #         }, ...
        #     ]
        # }

    def get_data(self):
        data = {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}

        if data.get("messages") is not None:
            data["messages"] = [message.get_data() for message in data["messages"]]

        return data

class Message():
    def __init__(self, from_customer=None, content=None, platform_type=None):
        self.from_customer = from_customer
        self.content = content
        self.platform_type = platform_type
        self.timestamp = common.get_current_timestamp()

    def get_data(self):
        return {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}
