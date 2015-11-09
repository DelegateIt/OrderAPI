from boto.dynamodb2.table import Table, Item
from boto.dynamodb2.exceptions import ConditionalCheckFailedException

import jsonpickle

import time
import json
import uuid

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
            raise ValueError("One or more of the item's data fields is invalid")

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
            raise ValueError("The Customer is not unique in the database")

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
