from boto.dynamodb2.table import Table

import jsonpickle

import time
import json
import uuid
from enum import Enum

from gator import service
from gator import common

##############################
# Global vars, consts, extra #
##############################

conn = service.dynamodb

# Tables
customers    = Table("DelegateIt_Customers",    connection=conn)
delegators   = Table("DelegateIt_Delegators",   connection=conn)
transactions = Table("DelegateIt_Transactions", connection=conn)
handlers     = Table("DelegateIt_Handlers",     connection=conn)

# Class that all models must be inheret from
class Model():
    # Attribute access
    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, val):
        if key in self.VALID_KEYS:
            self.setattr(self, key, val)
        else:
            raise ValueError("Attribute %s is not valid." % key)
    
    def get_data(self):
        raise NotImplementedError("Function get_data must be implemented by all subclasses");

    # Database Logic
    def save(self):
        # TODO : fix this later
        pass

    def create(self):
        print("Creating obj with the following data: %s" % self.get_data())
        self.TABLE.put_item(self.get_data())

    # Parsing and json
    def to_json(self):
        return jsonpickle.encode(get_data())


@unique
class CustomerFields(Enum):
    UUID = "uuid"
    PHONE_NUMBER = "phone_number"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    STRIPE_ID = "stripe_id"
    ACTIVE_TRANSACTION_UUIDS = "active_transaction_uuids"
    INACTIVE_TRANSACTION_UUIDS = "inactive_transaction_uuids" 

class Customer(Model):
    VALID_KEYS = [item[1].value for item in CustomerFields.__members__.items()]
    TABLE = customers
    
    def __init__(self, attributes):
        for atr, val in attributes.iteritems():
            if atr in CustomerFields.__members__.items():
                setattr(self, atr, val)
            else:
                raise ValueError("Attribute %s is not valid." % (atr))

    @staticmethod
    def create_new(attributes):
        customer = Customer(attributes)

        customer.uuid = get_uuid()
        customer.active_transaction_uuids = []
        customer.inactive_transaction_uuids = []

        return customer

    def get_data(self):
        data = {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}

        if data.get("active_transaction_uuids") is not None:
            data["active_transaction_uuids"] = [transaction.get_data() for transaction in data["active_transaction_uuids"]]

        if data.get("inactive_transaction_uuids") is not None:
            data["inactive_transaction_uuids"] = [transaction.get_data() for transaction in data["inactive_transaction_uuids"]]

        return data

    def is_unique(self):
        if self["phone_number"] is None:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self["phone_number") == 0

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
