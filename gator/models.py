from boto.dynamodb2.table import Table

import jsonpickle

import time
import json
import uuid

from gator import service, common, config

##############################
# Global vars, consts, extra #
##############################

conn = service.dynamodb

# Tables
table_prefix = config.store["dynamodb"]["table_prefix"]
customers    = Table(table_prefix + "DelegateIt_Customers",    connection=conn)
delegators   = Table(table_prefix + "DelegateIt_Delegators",   connection=conn)
transactions = Table(table_prefix + "DelegateIt_Transactions", connection=conn)
handlers     = Table(table_prefix + "DelegateIt_Handlers",     connection=conn)

class Customer():
    def __init__(self, phone_number=None, first_name=None, last_name=None,
            active_transaction_uuids=None, inactive_transaction_uuids=None,
            fbuser_id=None):
        self.uuid = common.get_uuid()
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name
        self.stripe_id = None
        self.fbuser_id = fbuser_id

        self.active_transaction_uuids = active_transaction_uuids
        self.inactive_transaction_uuids = inactive_transaction_uuids

    @staticmethod
    def create_from_dict(data):
        return Customer(
            phone_number=data.get("phone_number"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            active_transaction_uuids=data.get("active_transaction_uuids"),
            inactive_transaction_uuids=data.get("inactive_transaction_uuids"),
            fbuser_id=data.get("fbuser_id"))

    def get_data(self):
        data = {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}

        if data.get("active_transaction_uuids") is not None:
            data["active_transaction_uuids"] = [transaction.get_data() for transaction in data["active_transaction_uuids"]]

        if data.get("inactive_transaction_uuids") is not None:
            data["inactive_transaction_uuids"] = [transaction.get_data() for transaction in data["inactive_transaction_uuids"]]

        return data

    def is_unique(self):
        if self.phone_number is None:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self.phone_number) == 0

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
