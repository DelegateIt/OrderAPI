import unittest

import boto.dynamodb2
from boto.dynamodb2.table import Table

import apiclient

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
# apiclient.default_host = "backend-lb-125133299.us-west-2.elb.amazonaws.com"
apiclient.default_host = "localhost:80"

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

        customer_response_data = apiclient.create_customer("George","Farcasiu", "8176808185")

        # Verify that the response is correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertIsNotNone(customer_response_data["uuid"])

        # Check the db to make sure our data is correct
        customer = customers.get_item(uuid=customer_response_data["uuid"], consistent=True)
        self.assertEquals(customer["first_name"], "George")
        self.assertEquals(customer["last_name"],  "Farcasiu")

    def test_get_customer(self):
        customer_post_data = apiclient.create_customer("George","Farcasiu", "8176808185")
        customer_get_data = apiclient.get_customer(customer_post_data["uuid"])

        # Verify that the response is correct
        self.assertEquals(customer_post_data["result"], 0)
        self.assertEquals(customer_get_data["result"], 0)
        self.assertEquals(customer_get_data["first_name"], "George")
        self.assertEquals(customer_get_data["last_name"], "Farcasiu")
        self.assertEquals(customer_get_data["phone_number"], "8176808185")

    def test_send_message(self):
        customer_response_data = apiclient.create_customer("George","Farcasiu", "8176808185")
        customer_uuid = customer_response_data["uuid"]

        transaction_response_data = apiclient.create_transaction(customer_uuid)
        transaction_uuid = transaction_response_data["uuid"]


        message_get_response_data_1  = apiclient.get_messages(transaction_uuid)
        message_send_response_data = apiclient.send_message(transaction_uuid, platform_type="sms", content="test_send_message content")
        message_get_response_data_2  = apiclient.get_messages(transaction_uuid)

        # Verify that responses are correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_get_response_data_1["result"], 0)
        self.assertEquals(message_send_response_data["result"], 0)
        self.assertEquals(message_get_response_data_2["result"], 0)
        self.assertEquals(message_get_response_data_1["messages"], None)
        self.assertNotEquals(message_send_response_data["timestamp"], None)

        self.assertEquals(len(message_get_response_data_2["messages"]), 1)
        self.assertEquals(message_get_response_data_2["messages"][0]["transaction_uuid"], transaction_uuid)
        self.assertEquals(message_get_response_data_2["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(message_get_response_data_2["messages"][0].get("timestamp"))

        # Check the db to make sure our data is correct
        customer = customers.get_item(uuid=customer_uuid, consistent=True)
        self.assertIsNotNone(customer.get("messages"))
        self.assertEquals(len(customer["messages"]), 1)
        self.assertEquals(customer["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(customer["messages"][0]["timestamp"])

        self.assertEquals(message_get_response_data_2["messages"][0]["timestamp"], customer["messages"][0]["timestamp"])

    def test_get_messages_past_timestamp(self):
        customer_response_data = apiclient.create_customer("George","Farcasiu", "8176808185")
        customer_uuid = customer_response_data["uuid"]

        transaction_response_data = apiclient.create_transaction(customer_uuid)
        transaction_uuid = transaction_response_data["uuid"]

        message_response_data_1 = apiclient.send_message(transaction_uuid, platform_type="sms", content="test_send_message content 1")
        message_response_data_2 = apiclient.send_message(transaction_uuid, platform_type="sms", content="test_send_message content 2")

        message_get_response_data = apiclient.get_messages_past_timestamp(transaction_uuid, message_response_data_1["timestamp"])

        # Verify that response is correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_response_data_1["result"], 0)
        self.assertEquals(message_response_data_2["result"], 0)
        self.assertEquals(message_get_response_data["result"], 0)

        self.assertEquals(len(message_get_response_data["messages"]), 1)
        self.assertEquals(message_get_response_data["messages"][0]["content"], "test_send_message content 2")
        self.assertIsNotNone(message_get_response_data["messages"][0]["timestamp"])

    def test_transaction(self):
        customer_response_data = apiclient.create_customer("George","Farcasiu", "8176808185")
        customer_uuid = customer_response_data["uuid"]

        transaction_create_response = apiclient.create_transaction(customer_uuid)
        transaction_uuid = transaction_create_response["uuid"]

        transaction_get_response = apiclient.get_transaction(transaction_uuid)
        transaction_update_response = apiclient.update_transaction(transaction_uuid, "helped")

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
        uuid_1 = apiclient.create_customer("George","Farcasiu", "8176808180")["uuid"]
        uuid_2 = apiclient.create_customer("~George","~Farcasiu", "8176808185")["uuid"]
        apiclient.create_transaction(uuid_1, status="helped")
        apiclient.create_transaction(uuid_2)
        query_response = apiclient.get_transactions_with_status("helped")

        # Verify that the responses are correct
        self.assertEquals(query_response["result"], 0)
        self.assertEquals(len(query_response["transactions"]), 1)
        self.assertEquals(query_response["transactions"][0]["status"], "helped")

    def test_delegator(self):
        delegator_create_rsp = apiclient.create_delegator("George", "Farcasiu", "8176808185", "farcasiu.george@gmail.com")
        uuid = delegator_create_rsp["uuid"]

        delegator_get_rsp = apiclient.get_delegator(uuid)

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
