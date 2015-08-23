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
    def __init__(self, phone_number=None, first_name=None, last_name=None, messages=None):
        self.uuid = get_uuid()
        self.phone_number = phone_number
        self.first_name   = first_name
        self.last_name    = last_name

        if messages is not None:
            self.messages = messages

    def add_message(self, new_message):
        if not hasattr(self, "messages"):
            self.messages = []

        self.messages.append(new_message)

    def get_data(self):
        data = vars(self)

        if data.get("messages") is not None:
            data["messages"] = [message.get_data() for message in data["messages"]]

        return data

    def is_unique(self):
        if self.phone_number is None:
            return False

        return customers.query_count(index="phone_number-index", phone_number__eq=self.phone_number) == 0

    def __getitem__(self, val):
        return self.__dict__[val]

    def __repr__(self):
        to_return = "<Customer(first_name='%s', last_name='%s', phone_number='%s'" \
            % (self.first_name, self.last_name, self.phone_number)

        if hasattr(self, "messages"):
            to_return += ", messages=[%s])>" % ",\n\t".join([str(message) for message in self.messages])
        else:
            to_return += ">"

        return to_return

class Message():
    def __init__(self, content=None, platform_type=None):
        self.content = content
        self.timestamp = get_current_timestamp()
        self.platform_type = platform_type

    def get_data(self):
        return vars(self)

    def __getitem__(self, val):
        return self.__dict__[val]

    def __repr__(self):
        return "<Message(content='%s', timestamp='%s')>" % (
            self.content, self.timestamp)

class Delegator():
    def __init__(self, phone_number=None, first_name=None, last_name=None, num_transactions=None):
        self.uuid = get_uuid()
        self.phone_number = phone_number
        self.first_name   = first_name
        self.last_name    = last_name

        if num_transactions is not None:
            self.num_transactions = 0

    def get_data(self):
        return vars(self)

    def __getitem__(self, val):
        return self.__dict__[val]

    def __repr__(self):
        return "<Delegator(first_name='%s', last_name='%s', phone_number='%s')>" % (
            self.first_name, self.last_name, self.phone_number)

class Transaction():
    def __init__(self, customer_uuid=None, status=None, delegator_uuid=None):
        self.uuid = get_uuid()
        self.customer_uuid = customer_uuid
        self.status = status
        self.timestamp = get_current_timestamp()

        if delegator_uuid is not None:
            self.delegator_uuid = delegator_uuid

    def get_data(self):
        return vars(self)

    def to_json(self):
        return json.dumps(get_data)

    def __getitem__(self, val):
        return self.__dict__[val]

    def __repr__(self):
        to_return = "<Transaction(customer_phone_number='%s', status='%s'" % (
            self.customer_phone_number, self.status)

        if self.delegator_uuid is not None:
            to_return += ", delegator_uuid='%s')>" % self.delegator_uuid
        else:
            to_return += ">"

        return to_return

####################
# Helper Functions #
####################

def get_current_timestamp():
    return int(time.time() * 10**6)

def get_uuid():
    return str(uuid.uuid4().int >> 64)
