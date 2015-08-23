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
server_url = "http://127.0.0.1:80"

def clear():
    for table in [customers, delegators, transactions]:
        for item in table.scan():
            item.delete()

class TestBasicRestFunctionality(unittest.TestCase):
    def setUp(self):
        clear()

    def tearDown(self):
        clear()

    def test_create_customer(self):
        customer_json_data = json.dumps({
            "phone_number": "8176808185",
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        customer_response_data = requests.post("%s/customer" % (server_url), customer_json_data).json()

        # Verify that the response is correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertIsNotNone(customer_response_data["uuid"])

        # Check the db to make sure our data is correct
        customer = customers.get_item(uuid=customer_response_data["uuid"], consistent=True)
        self.assertEquals(customer["first_name"], "George")
        self.assertEquals(customer["last_name"],  "Farcasiu")

    def test_get_customer(self):
        customer_json_data = json.dumps({
            "phone_number": "8176808185",
            "first_name": "George",
            "last_name":  "Farcasiu"
        })


        customer_post_data = requests.post("%s/customer" % (server_url), customer_json_data).json()
        customer_get_data = requests.get("%s/customer/%s" % (server_url, customer_post_data["uuid"])).json()

        # Verify that the response is correct
        self.assertEquals(customer_post_data["result"], 0)
        self.assertEquals(customer_get_data["result"], 0)
        self.assertEquals(customer_get_data["first_name"], "George")
        self.assertEquals(customer_get_data["last_name"], "Farcasiu")
        self.assertEquals(customer_get_data["phone_number"], "8176808185")

    def test_send_message(self):
        customer_json_data = json.dumps({
            "phone_number": "8176808185",
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        message_json_data = json.dumps({
            "platform_type": "sms",
            "content": "test_send_message content"
        })

        customer_response_data = requests.post("%s/customer" % (server_url), customer_json_data).json()
        uuid = customer_response_data["uuid"]

        message_get_response_data_1  = requests.get("%s/get_messages/%s" % (server_url, uuid)).json()
        message_send_response_data = requests.post("%s/send_message/%s" % (server_url, uuid), message_json_data).json()
        message_get_response_data_2  = requests.get("%s/get_messages/%s" % (server_url, uuid)).json()

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
        customer = customers.get_item(uuid=uuid, consistent=True)
        self.assertIsNotNone(customer.get("messages"))
        self.assertEquals(len(customer["messages"]), 1)
        self.assertEquals(customer["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(customer["messages"][0]["timestamp"])

        self.assertEquals(message_get_response_data_2["messages"][0]["timestamp"], customer["messages"][0]["timestamp"])

    def test_get_message_past_timestamp(self):
        customer_json_data = json.dumps({
            "phone_number": "8176808185",
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

        customer_response_data = requests.post("%s/customer" % (server_url), customer_json_data).json()
        uuid = customer_response_data["uuid"]

        message_response_data_1 = requests.post("%s/send_message/%s" % (server_url, uuid), message_json_data_1).json()
        message_response_data_2 = requests.post("%s/send_message/%s" % (server_url, uuid), message_json_data_2).json()

        message_get_response_data = requests.get("%s/get_messages_past_timestamp/%s/%s" % (server_url, uuid, message_response_data_1["timestamp"])).json()

        # Verify that response is correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_response_data_1["result"], 0)
        self.assertEquals(message_response_data_2["result"], 0)
        self.assertEquals(message_get_response_data["result"], 0)

        self.assertEquals(len(message_get_response_data["messages"]), 1)
        self.assertEquals(message_get_response_data["messages"][0]["content"], "test_send_message content 2")
        self.assertIsNotNone(message_get_response_data["messages"][0]["timestamp"])

    def test_transaction(self):
        customer_json_data = json.dumps({
            "phone_number": "8176808185",
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        transaction_update_json_data = json.dumps({
            "status": "helped"
        })

        customer_response_data = requests.post("%s/customer" % (server_url), customer_json_data).json()
        customer_uuid = customer_response_data["uuid"]

        transaction_create_response = requests.post("%s/transaction" % server_url,
                json.dumps({"customer_uuid": customer_uuid})).json()
        transaction_uuid = transaction_create_response["uuid"]

        transaction_get_response = requests.get("%s/transaction/%s" % (server_url, transaction_uuid)).json()
        transaction_update_response = requests.put("%s/transaction/%s" % (server_url, transaction_uuid), transaction_update_json_data).json()

        # Verify that the response
        self.assertEquals(transaction_create_response["result"], 0)
        self.assertIsNotNone(transaction_create_response["uuid"])
        self.assertEquals(transaction_get_response["result"], 0)
        self.assertEquals(transaction_update_response["result"], 0)

        self.assertEquals(transaction_get_response["transaction"]["customer_uuid"], customer_uuid)
        self.assertEquals(transaction_get_response["transaction"]["status"], "started") # old value
        self.assertEquals(transaction_get_response["transaction"].get("delegator_uuid"), None)

        # Verify that information in the db is correct
        transaction = transactions.get_item(uuid=transaction_uuid)
        self.assertEquals(transaction["customer_uuid"], customer_uuid)
        self.assertEquals(transaction["status"], "helped")

    def test_get_transactions_with_status(self):
        customer_json_data_1 = json.dumps({
            "phone_number": "8176808180",
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        customer_json_data_2 = json.dumps({
            "phone_number": "8176808185",
            "first_name": "~George",
            "last_name":  "~Farcasiu"
        })

        uuid_1 = requests.post("%s/customer" % (server_url), customer_json_data_1).json()["uuid"]
        uuid_2 = requests.post("%s/customer" % (server_url), customer_json_data_2).json()["uuid"]
        requests.post("%s/transaction" % (server_url), json.dumps({"customer_uuid": uuid_1, "status": "helped"}))
        requests.post("%s/transaction" % (server_url), json.dumps({"customer_uuid": uuid_2}))
        query_response = requests.get("%s/get_transactions_with_status/%s" % (server_url, "helped")).json()

        # Verify that the responses are correct
        self.assertEquals(query_response["result"], 0)
        self.assertEquals(len(query_response["transactions"]), 1)
        self.assertEquals(query_response["transactions"][0]["status"], "helped")

    def test_delegator(self):
        delegator_json = json.dumps({
            "phone_number": "8176808185",
            "email": "farcasiu.george@gmail.com",
            "first_name": "George",
            "last_name": "Farcasiu"
        })

        delegator_create_rsp = requests.post("%s/delegator" % (server_url), delegator_json).json()
        uuid = delegator_create_rsp["uuid"]

        delegator_get_rsp = requests.get("%s/delegator/%s" % (server_url, uuid)).json()

        # Verify that the rsp is correct
        self.assertIsNotNone(uuid)
        self.assertEquals(delegator_create_rsp["result"], 0)
        self.assertEquals(delegator_get_rsp["uuid"], uuid)
        self.assertEquals(delegator_get_rsp["phone_number"], "8176808185")
        self.assertEquals(delegator_get_rsp["email"], "farcasiu.george@gmail.com")
        self.assertEquals(delegator_get_rsp["first_name"], "George")
        self.assertEquals(delegator_get_rsp["last_name"], "Farcasiu")
        self.assertEquals(delegator_get_rsp["num_transactions"], 0)

        # Verify that the db contains the correct information
        delegator = delegators.get_item(uuid=uuid, consistent=True)
        self.assertEquals(delegator["phone_number"], "8176808185")
        self.assertEquals(delegator["first_name"], "George")
        self.assertEquals(delegator["last_name"], "Farcasiu")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBasicRestFunctionality)
    unittest.TextTestRunner(verbosity=2).run(suite)
