import nose
from gator import apiclient
from endpoint.rest import RestTest

class TransactionTest(RestTest):

    def create(self):
        rsp = apiclient.create_transaction(self.customer_uuid)
        self.assertResponse(0, rsp)
        return rsp

    def setUp(self):
        apiclient.clear_database()
        rsp1 = apiclient.create_customer("customerFirstName", "customerLastName", "15555555551", "1", "")
        rsp2 = apiclient.create_delegator("delegatorFirstName", "delegatorLastName", "15555555552",
                "noreply@gmail.com", "2", "")
        self.assertResponse(0, rsp1)
        self.assertResponse(0, rsp2)
        self.customer_uuid = rsp1["uuid"]
        self.delegator_uuid = rsp2["uuid"]

    def test_create(self):
        #TODO test status is valid
        uuid1 = self.create()["uuid"]

        self.assertResponse(0, apiclient.get_transaction(uuid1))
        self.assertResponse(10, apiclient.create_transaction("fake uuid"))

        customer_transactions = apiclient.get_customer(self.customer_uuid)["customer"]["active_transaction_uuids"]
        self.assertTrue([uuid1] == customer_transactions, "The customer object was not updated")

    def test_retreive(self):
        uuid = self.create()["uuid"]
        transaction = apiclient.get_transaction(uuid)
        expected = {
            "result": 0,
            "transaction": {
                "uuid": uuid,
                "status": "started",
                "customer_uuid": transaction["transaction"]["customer_uuid"],
                "payment_url": transaction["transaction"]["payment_url"],
                "timestamp": transaction["transaction"]["timestamp"]
            }
        }
        self.assertEqual(expected, transaction)

    def test_update_status(self):
       transaction_uuid = self.create()["uuid"]
       apiclient.update_transaction(transaction_uuid, delegator_uuid=self.delegator_uuid)
       delegator = apiclient.get_delegator(self.delegator_uuid)
       self.assertEqual([transaction_uuid], delegator["delegator"]["active_transaction_uuids"])
       self.assertFalse("inactive_transaction_uuids" in delegator)
       customer = apiclient.get_customer(self.customer_uuid)
       self.assertEqual([transaction_uuid], customer["customer"]["active_transaction_uuids"])
       self.assertFalse("inactive_transaction_uuids" in customer)

       apiclient.update_transaction(transaction_uuid, status="completed")

       delegator = apiclient.get_delegator(self.delegator_uuid)
       print ("delegator: %s" % delegator)
       print ("transaction: %s" % apiclient.get_transaction(transaction_uuid))
       self.assertEqual([transaction_uuid], delegator["delegator"]["inactive_transaction_uuids"])
       self.assertFalse("active_transaction_uuids" in delegator)
       customer = apiclient.get_customer(self.customer_uuid)
       self.assertEqual([transaction_uuid], customer["customer"]["inactive_transaction_uuids"])
       self.assertFalse("active_transaction_uuids" in customer)

    def test_update_delegator(self):
       transaction_uuid = self.create()["uuid"]
       apiclient.update_transaction(transaction_uuid, delegator_uuid=self.delegator_uuid)
       delegator_uuid2 = apiclient.create_delegator("asf", "asdf", "15555555553", "no.reply@gmail.com",
            fbuser_id="123123", fbuser_token="")["uuid"]
       delegator1 = apiclient.get_delegator(self.delegator_uuid)
       delegator2 = apiclient.get_delegator(delegator_uuid2)
       self.assertEqual([transaction_uuid], delegator1["delegator"]["active_transaction_uuids"])
       self.assertFalse("inactive_transaction_uuids" in delegator1)
       self.assertFalse("active_transaction_uuids" in delegator2)
       self.assertFalse("inactive_transaction_uuids" in delegator2)

       apiclient.update_transaction(transaction_uuid, delegator_uuid=delegator_uuid2)

       delegator1 = apiclient.get_delegator(self.delegator_uuid)
       delegator2 = apiclient.get_delegator(delegator_uuid2)
       self.assertEqual([transaction_uuid], delegator2["delegator"]["active_transaction_uuids"])
       self.assertFalse("inactive_transaction_uuids" in delegator2)
       self.assertFalse("active_transaction_uuids" in delegator1)
       self.assertFalse("inactive_transaction_uuids" in delegator1)
       self.assertEqual(delegator_uuid2, apiclient.get_transaction(transaction_uuid)["transaction"]["delegator_uuid"])

       apiclient.update_transaction(transaction_uuid, status="completed")
       apiclient.update_transaction(transaction_uuid, delegator_uuid=self.delegator_uuid)

       delegator1 = apiclient.get_delegator(self.delegator_uuid)
       delegator2 = apiclient.get_delegator(delegator_uuid2)
       self.assertEqual([transaction_uuid], delegator1["delegator"]["inactive_transaction_uuids"])
       self.assertFalse("active_transaction_uuids" in delegator1)
       self.assertFalse("active_transaction_uuids" in delegator2)
       self.assertFalse("inactive_transaction_uuids" in delegator2)

    def test_send_message(self):
        transaction_uuid = self.create()["uuid"]
        apiclient.send_message(transaction_uuid, platform_type="test", from_customer=True, content="test1")
        messages = apiclient.get_transaction(transaction_uuid)["transaction"]["messages"]
        expected = [{
            "platform_type": "test",
            "content": "test1",
            "from_customer": True,
            "timestamp": messages[0]["timestamp"]
        }]
        apiclient.send_message(transaction_uuid, platform_type="test", from_customer=False, content="test2")
        messages = apiclient.get_transaction(transaction_uuid)["transaction"]["messages"]
        expected.append({
            "platform_type": "test",
            "content": "test2",
            "from_customer": False,
            "timestamp": messages[1]["timestamp"]
        })

