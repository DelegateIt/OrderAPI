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
    def __init__(self, phone_number=None, first_name=None, last_name=None, messages=None):
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
    def __init__(self, content=None, timestamp=None):
        self.content = content
        self.timestamp = get_current_timestamp() if timestamp is None else timestamp

    def get_data(self):
        return vars(self)

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

def create_customer_from_item(item):
    customer = Customer()

    for key in customer.get_data():
        customer[key] = item[key]

    if item.get("messages") is not None:
        customer["messages"] = []
        for message in item["messages"]:
            customer["messages"].append(Message(
                content=message["content"], timestamp=message["timestamp"]))

    return customer


if __name__ == "__main__":
    customer = Customer(first_name="George", last_name="Farcasiu", phone_number="8176808185", messages=[Message("This is a message")])
    print customer.get_data()
