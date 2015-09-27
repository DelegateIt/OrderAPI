import unittest

import boto.dynamodb2
from boto.dynamodb2.table import Table

import apiclient

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="",
        aws_secret_access_key="")

# Tables
customers    = Table("DelegateIt_Customers", connection=conn)
delegators   = Table("DelegateIt_Delegators", connection=conn)
transactions = Table("DelegateIt_Transactions", connection=conn)
handlers     = Table("DelegateIt_Handlers", connection=conn)

# Service configs
# apiclient.default_host = "backend-lb-125133299.us-west-2.elb.amazonaws.com"
apiclient.default_host = "localhost:8080"

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
        customer_response_data = apiclient.create_customer("George", "Farcasiu", "8176808185")

        # Verify that the response is correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertIsNotNone(customer_response_data["uuid"])

        # Check the db to make sure our data is correct
        customer = customers.get_item(uuid=customer_response_data["uuid"], consistent=True)
        self.assertEquals(customer["first_name"], "George")
        self.assertEquals(customer["last_name"],  "Farcasiu")
        self.assertEquals(customer["phone_number"], "8176808185")

    def test_get_customer(self):
        customer_post_data = apiclient.create_customer("George","Farcasiu", "8176808185")
        customer_get_data = apiclient.get_customer(customer_post_data["uuid"])

        # Verify that the response is correct
        self.assertEquals(customer_post_data["result"], 0)
        self.assertEquals(customer_get_data["result"], 0)

        self.assertEquals(customer_get_data["first_name"], "George")
        self.assertEquals(customer_get_data["last_name"], "Farcasiu")
        self.assertEquals(customer_get_data["phone_number"], "8176808185")
        self.assertIsNone(customer_get_data.get("transactions"))

    def test_send_message(self):
        customer_response_data = apiclient.create_customer("George", "Farcasiu", "8176808185")
        customer_uuid = customer_response_data["uuid"]

        transaction_response_data = apiclient.create_transaction(customer_uuid)
        transaction_uuid = transaction_response_data["uuid"]

        message_get_response_data_1  = apiclient.get_messages(transaction_uuid)
        message_send_response_data = apiclient.send_message(transaction_uuid, platform_type="sms", content="test_send_message content", from_customer=True)
        message_get_response_data_2  = apiclient.get_messages(transaction_uuid)

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
        self.assertTrue(message_get_response_data_2["messages"][0]["from_customer"])

        # Check the db to make sure our data is correct
        transaction = transactions.get_item(uuid=transaction_uuid, consistent=True)
        self.assertIsNotNone(transaction.get("messages"))
        self.assertEquals(len(transaction["messages"]), 1)
        self.assertEquals(transaction["messages"][0]["content"], "test_send_message content")
        self.assertIsNotNone(transaction["messages"][0]["timestamp"])

        self.assertEquals(message_get_response_data_2["messages"][0]["timestamp"], transaction["messages"][0]["timestamp"])

    def test_transaction(self):
        delegator_create_rsp = apiclient.create_delegator("George", "Farcasiu", "8176808185", "farcasiu.george@gmail.com")
        customer_response_data = apiclient.create_customer("George","Farcasiu", "8176808185")
        customer_uuid = customer_response_data["uuid"]

        transaction_create_response = apiclient.create_transaction(customer_uuid)
        transaction_uuid = transaction_create_response["uuid"]

        update_delegator = apiclient.update_transaction(transaction_uuid, delegator_uuid=delegator_create_rsp["uuid"])
        #Special case when changing the transaction to/from inactive to/from active status
        update_status = apiclient.update_transaction(transaction_uuid, "completed")
        transaction_update_response = apiclient.update_transaction(transaction_uuid, "helped")
        transaction_get_response = apiclient.get_transaction(transaction_uuid)

        # Verify that the response
        self.assertEquals(transaction_create_response["result"], 0)
        self.assertIsNotNone(transaction_create_response["uuid"])
        self.assertEquals(transaction_get_response["result"], 0)
        self.assertEquals(transaction_update_response["result"], 0)
        self.assertEquals(update_status["result"], 0)
        self.assertEquals(update_delegator["result"], 0)

        self.assertEquals(transaction_get_response["transaction"]["customer_uuid"], customer_uuid)
        self.assertIsNotNone(transaction_get_response["transaction"]["payment_url"])
        self.assertEquals(transaction_get_response["transaction"]["status"], "helped")
        self.assertEquals(transaction_get_response["transaction"].get("delegator_uuid"), delegator_create_rsp["uuid"])

        # Verify that information in the db is correct
        transaction = transactions.get_item(uuid=transaction_uuid)
        self.assertEquals(transaction["customer_uuid"], customer_uuid)
        self.assertEquals(transaction["status"], "helped")

        # Verify active/inactive lists get updated
        self.assertTrue(transaction_uuid in apiclient.get_customer(customer_response_data["uuid"])["active_transaction_uuids"])
        apiclient.update_transaction(transaction_uuid, "completed")
        self.assertTrue(transaction_uuid in apiclient.get_customer(customer_response_data["uuid"])["inactive_transaction_uuids"])

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
        self.assertIsNone(delegator_get_rsp.get("transactions"))

        # Verify that the db contains the correct information
        delegator = delegators.get_item(uuid=uuid, consistent=True)
        self.assertEquals(delegator["phone_number"], "8176808185")
        self.assertEquals(delegator["first_name"], "George")
        self.assertEquals(delegator["last_name"], "Farcasiu")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBasicRestFunctionality)
    unittest.TextTestRunner(verbosity=2).run(suite)
