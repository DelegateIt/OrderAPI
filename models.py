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
    def __init__(self, phone_number=None, first_name=None, last_name=None,
            active_transaction_uuids=None, inactive_transaction_uuids=None):
        self.uuid = get_uuid()
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name
        self.stripe_id = None

        self.active_transaction_uuids = active_transaction_uuids
        self.inactive_transaction_uuids = inactive_transaction_uuids

    @staticmethod
    def create_from_dict(data):
        return Customer(
            phone_number=data.get("phone_number"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            active_transaction_uuids=data.get("active_transaction_uuids"),
            inactive_transaction_uuids=data.get("inactive_transaction_uuids"))

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
        self.uuid = get_uuid()
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
        self.uuid = get_uuid()
        self.customer_uuid = customer_uuid
        self.delegator_uuid = delegator_uuid
        self.status = status
        self.timestamp = get_current_timestamp()
        self.messages = messages
        self.receipt = None
        #receipt = {
        #    paid: boolean,
        #    items: [
        #        {
        #            name: string,
        #            cents: int, cost of item in pennies
        #        }, ...
        #    ]
        #}

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
        self.timestamp = get_current_timestamp()

    def get_data(self):
        return {key: vars(self)[key] for key in vars(self) if vars(self)[key] is not None}

####################
# Helper Functions #
####################

def get_current_timestamp():
    return int(time.time() * 10**6)

def get_uuid():
    return str(uuid.uuid4().int >> 64)
