import boto.dynamodb2
from boto.dynamodb2.table import Table

import time
import json

import jsonpickle

##############################
# Global vars, consts, extra #
##############################

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
        aws_secret_access_key="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")

# Tables
customers = Table("DelegateIt_Customers", connection=conn)

class Customer():
    def __init__(self, first_name, last_name, phone_number, messages=None):
        self.customer_id = get_current_timestamp()
        self.first_name  = first_name
        self.last_name   = last_name
        self.phone_number = phone_number
        self.messages    = messages if messages is not None else []

    def add_message(self, new_message):
        self.messages.append(new_message)

    def get_data(self):
        return self.__dict__

    def __getitem__(self, val):
        return self.__dict__[val]

    def __repr__(self):
        return "<Customer(first_name='%s', last_name='%s', phone_number='%s', messages=[%s])>" % (
            self.first_name, self.last_name, self.phone_number,
            ",\n\t".join([str(message) for message in self.messages]))

class Message():
    def __init__(self, content):
        self.content = content
        self.timestamp = get_current_timestamp()

    def __getitem__(self, val):
        return self.__dict__[val]

    def __repr__(self):
        return "<Message(content='%s', timestamp='%s')>" % (
            self.content, self.timestamp)

####################
# Helper Functions #
####################

def get_current_timestamp():
    return int(time.time() * 10**6)
