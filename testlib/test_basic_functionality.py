import unittest

import boto.dynamodb2
from boto.dynamodb2.table import Table
from boto.dynamodb.batch import BatchWrite

import re
import requests, json
import subprocess, os, signal

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
        aws_secret_access_key="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")

# Tables
customers    = Table("DelegateIt_Customers", connection=conn)
delegators   = Table("DelegateIt_Delegators", connection=conn)
transactions = Table("DelegateIt_Transactions", connection=conn)

# Service configs
server_url = "http://127.0.0.1:8080"

def clear():
    for table in [customers, delegators, transactions]:
        for item in table.scan():
            item.delete()

class TestBasicRestFunctionality(unittest.TestCase):
    def setUp(self):
        clear()

    def tearDown(self):
        #clear()
        pass

    def test_create_customer(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        phone_number = "8176808185"

        customer_response_data = requests.post("%s/customer/%s" % (server_url, phone_number), customer_json_data).json()

        # Verify that the response is correct
        self.assertEquals(customer_response_data["result"], 0)

        # Check the db to make sure our data is correct
        customer = customers.get_item(phone_number=phone_number, consistent=True)
        self.assertEquals(customer["first_name"], "George")
        self.assertEquals(customer["last_name"],  "Farcasiu")

    def test_get_customer(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        phone_number = "8176808185"

        customer_post_data = requests.post("%s/customer/%s" % (server_url, phone_number), customer_json_data).json()
        customer_get_data = requests.get("%s/customer/%s" % (server_url, phone_number)).json()

        # Verify that the response is correct
        self.assertEquals(customer_post_data["result"], 0)
        self.assertEquals(customer_get_data["result"], 0)
        self.assertEquals(customer_get_data["first_name"], "George")
        self.assertEquals(customer_get_data["last_name"], "Farcasiu")
        self.assertEquals(customer_get_data["phone_number"], phone_number)

    def test_send_message(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        message_json_data = json.dumps({
            "platform_type": "sms",
            "content": "test_send_message content"
        })

        phone_number = "8176808185"

        customer_response_data = requests.post("%s/customer/%s" % (server_url, phone_number), customer_json_data).json()
        message_get_response_data_1  = requests.get("%s/get_messages/%s" % (server_url, phone_number)).json()
        message_send_response_data = requests.post("%s/send_message/%s" % (server_url, phone_number), message_json_data).json()
        message_get_response_data_2  = requests.get("%s/get_messages/%s" % (server_url, phone_number)).json()

        # Verify that responses are correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_get_response_data_1["result"], 0)
        self.assertEquals(message_send_response_data["result"], 0)
        self.assertEquals(message_get_response_data_2["result"], 0)
        self.assertEquals(message_get_response_data_1["messages"], None)
        self.assertNotEquals(message_send_response_data["timestamp"], None)

        self.assertEquals(len(message_get_response_data_2["messages"]), 1)
        self.assertEquals(message_get_response_data_2["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(message_get_response_data_2["messages"][0].get("timestamp"))

        # Check the db to make sure our data is correct
        customer = customers.get_item(phone_number=phone_number, consistent=True)
        self.assertIsNotNone(customer.get("messages"))
        self.assertEquals(len(customer["messages"]), 1)
        self.assertEquals(customer["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(customer["messages"][0]["timestamp"])

        self.assertEquals(message_get_response_data_2["messages"][0]["timestamp"], customer["messages"][0]["timestamp"])

    def test_get_message_past_timestamp(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        message_json_data_1 = json.dumps({
            "platform_type": "sms",
            "content": "test_send_message content 1"
        })

        message_json_data_2 = json.dumps({
            "platform_type": "sms",
            "content": "test_send_message content 2"
        })

        phone_number = "8176808185"

        customer_response_data = requests.post("%s/customer/%s" % (server_url, phone_number), customer_json_data).json()
        message_response_data_1 = requests.post("%s/send_message/%s" % (server_url, phone_number), message_json_data_1).json()
        message_response_data_2 = requests.post("%s/send_message/%s" % (server_url, phone_number), message_json_data_2).json()

        message_get_response_data = requests.get("%s/get_messages_past_timestamp/%s/%s" % (server_url, phone_number, message_response_data_1["timestamp"])).json()

        # Verify that response is correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_response_data_1["result"], 0)
        self.assertEquals(message_response_data_2["result"], 0)
        self.assertEquals(message_get_response_data["result"], 0)

        self.assertEquals(len(message_get_response_data["messages"]), 1)
        self.assertEquals(message_get_response_data["messages"][0]["content"], "test_send_message content 2")
        self.assertIsNotNone(message_get_response_data["messages"][0]["timestamp"])

    def test_transaction(self):
        phone_number = "8176808185"

        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        requests.post("%s/customer/%s" % (server_url, phone_number), customer_json_data)
        transaction_create_response = requests.post("%s/transaction/%s" % (server_url, phone_number), json.dumps({})).json()
        transaction_get_response = requests.get("%s/transaction/%s" % (server_url, phone_number)).json()

        # Verify that the response
        self.assertEquals(transaction_create_response["result"], 0)
        self.assertEquals(transaction_get_response["result"], 0)

        self.assertEquals(transaction_get_response["customer_phone_number"], phone_number)
        self.assertEquals(transaction_get_response["status"], 0)
        self.assertEquals(transaction_get_response["delegator_phone_number"], None)

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBasicRestFunctionality)
    unittest.TextTestRunner(verbosity=2).run(suite)
