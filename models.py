import boto.dynamodb2
from boto.dynamodb2.table import Table

import jsonpickle

import time
import json
import uuid

##############################
# Global vars, consts, extra #
##############################

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
        aws_secret_access_key="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")

# Tables
customers    = Table("DelegateIt_Customers",    connection=conn)
delegators   = Table("DelegateIt_Delegators",   connection=conn)
transactions = Table("DelegateIt_Transactions", connection=conn)

class Customer():
    def __init__(self, phone_number=None, first_name=None, last_name=None, transaction_uuids=None):
        self.uuid = get_uuid()
        self.phone_number = phone_number
        self.first_name   = first_name
        self.last_name    = last_name

        if transaction_uuids is not None:
            self.transaction_uuids = transaction_uuids

    def add_transaction_uuid(self, new_transaction_uuid):
        if not hasattr(self, "transaction_uuids"):
            self.transaction_uuids = []

        self.transaction_uuids.append(new_transaction)

    def get_data(self):
        data = vars(self)

        if data.get("transaction_uuids") is not None:
            data["transaction_uuids"] = [transaction.get_data() for transaction in data["transaction_uuids"]]

        return data

    def is_unique(self):
        if self.phone_number is None:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self.phone_number) == 0

    def __getitem__(self, val):
        return self.__dict__[val]

class Message():
    def __init__(self, from_customer=None, content=None, platform_type=None):
        self.from_customer = from_customer
        self.content = content
        self.platform_type = platform_type
        self.timestamp = get_current_timestamp()

    def get_data(self):
        return vars(self)

    def __getitem__(self, val):
        return self.__dict__[val]

class Delegator():
    def __init__(self, phone_number=None, email=None, first_name=None, last_name=None, transactions=None):
        self.uuid = get_uuid()
        self.phone_number = phone_number
        self.email = email
        self.first_name   = first_name
        self.last_name    = last_name

        if transactions is not None:
            self.transactions = transactions

    def get_data(self):
        data = vars(self)

        if data.get("transactions") is not None:
            data["transactions"] = [transaction.get_data() for transaction in data["transactions"]]

        return data

    def is_unique(self):
        if self.phone_number is None or self.email is None:
            return False

        phone_number_is_uniq = delegators.query_count(index="phone_number-index", phone_number__eq=self.phone_number) == 0
        email_is_uniq   = delegators.query_count(index="email-index", email__eq=self.email) == 0

        return phone_number_is_uniq and email_is_uniq

    def __getitem__(self, val):
        return self.__dict__[val]

class Transaction():
    def __init__(self, customer_uuid=None, delegator_uuid=None, status=None, messages=None):
        self.uuid = get_uuid()
        self.customer_uuid = customer_uuid
        self.status = status
        self.timestamp = get_current_timestamp()

        if delegator_uuid is not None:
            self.delegator_uuid = delegator_uuid

        if messages is not None:
            self.messages = messages

    def get_data(self):
        data = vars(self)

        if data.get("messages") is not None:
            data["messages"] = [message.get_data() for message in data["messages"]]

        return data

    def __getitem__(self, val):
        return self.__dict__[val]

####################
# Helper Functions #
####################

def get_current_timestamp():
    return int(time.time() * 10**6)

def get_uuid():
    return str(uuid.uuid4().int >> 64)
