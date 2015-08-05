import unittest

import boto.dynamodb2
from boto.dynamodb2.table import Table

import re
import requests, json
import subprocess, os, signal

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
        aws_secret_access_key="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")

# Tables
customers = Table("DelegateIt_Customers", connection=conn)

def clear():
    for customer in customers.scan():
        customer.delete()

class TestBasicRestFunctionality(unittest.TestCase):
    def setUp(self):
        clear()

    def tearDown(self):
        clear()

    def test_create_customer(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        phone_number = "8176808185"

        customer_response_data = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()

        # Verify that the response is correct
        self.assertEquals(customer_response_data["result"], 0)

        # Check the db to make sure our data is correct
        customer = customers.get_item(phone_number=phone_number)
        self.assertEquals(customer["first_name"], "George")
        self.assertEquals(customer["last_name"],  "Farcasiu")

    def test_get_customer(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        phone_number = "8176808185"

        customer_post = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()
        customer_get_response_data = requests.get("http://localhost:8080/customer/%s" % phone_number).json()

        # Verify that the response is correct
        self.assertEquals(customer_get_response_data["first_name"], "George")
        self.assertEquals(customer_get_response_data["last_name"], "Farcasiu")
        self.assertEquals(customer_get_response_data["phone_number"], phone_number)

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

        customer_response_data = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()
        message_get_response_data_1  = requests.get("http://localhost:8080/get_messages/%s" % phone_number).json()
        message_send_response_data = requests.post("http://localhost:8080/send_message/%s" % phone_number, message_json_data).json()
        message_get_response_data_2  = requests.get("http://localhost:8080/get_messages/%s" % phone_number).json()

        # Verify that responses are correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_get_response_data_1, None)
        self.assertEquals(message_send_response_data["result"], 0)
        self.assertNotEquals(message_send_response_data["timestamp"], None)

        self.assertEquals(len(message_get_response_data_2), 1)
        self.assertEquals(message_get_response_data_2[0]["content"], "test_send_message content")
        self.assertIsNotNone(message_get_response_data_2[0].get("timestamp"))

        # Check the db to make sure our data is correct
        customer = customers.get_item(phone_number=phone_number)
        self.assertIsNotNone(customer.get("messages"))
        self.assertEquals(len(customer["messages"]), 1)
        self.assertEquals(customer["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(customer["messages"][0]["timestamp"])

        self.assertEquals(message_get_response_data_2[0]["timestamp"], customer["messages"][0]["timestamp"])

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

        customer_response_data = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()
        message_response_data_1 = requests.post("http://localhost:8080/send_message/%s" % phone_number, message_json_data_1).json()
        message_response_data_2 = requests.post("http://localhost:8080/send_message/%s" % phone_number, message_json_data_2).json()

        message_get_response_data = requests.get("http://localhost:8080/get_messages_past_timestamp/%s/%s" % (phone_number, message_response_data_1["timestamp"])).json()

        # Verify that response is correct
        self.assertEquals(len(message_get_response_data), 1)
        self.assertEquals(message_get_response_data[0]["content"], "test_send_message content 2")
        self.assertIsNotNone(message_get_response_data[0]["timestamp"])

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBasicRestFunctionality)
    unittest.TextTestRunner(verbosity=2).run(suite)
