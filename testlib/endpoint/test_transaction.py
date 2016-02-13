import nose
import requests
import urllib.parse
from gator import apiclient
from endpoint.rest import RestTest

class TransactionTest(RestTest):
    def create(self):
        rsp = apiclient.create_transaction(self.customer_uuid, self.customer_platform_type)
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
        self.customer_platform_type = "sms"

    def test_receipt(self):
        uuid = self.create()["uuid"]
        receipt = {
            "total": 100,
            "items": [{
                "Pizza": 90
            }]
        }
        rsp = apiclient.update_transaction(uuid, receipt=receipt, status="proposed")
        self.assertResponse(0, rsp)

        rsp = apiclient.get_transaction(uuid)
        self.assertResponse(0, rsp)
        self.assertEqual(rsp["transaction"]["receipt"], receipt)
        self.assertEqual(rsp["transaction"]["status"], "proposed")

        #Pretend that the transaction was paid for
        receipt["stripe_charge_id"] = "131k23jljsf123"
        rsp = apiclient.update_transaction(uuid, receipt=receipt)
        self.assertResponse(0, rsp)

        rsp = apiclient.get_transaction(uuid)
        self.assertResponse(0, rsp)
        self.assertEqual(rsp["transaction"]["receipt"], receipt)

        rsp = apiclient.update_transaction(uuid, receipt=receipt)
        self.assertResponse(7, rsp)

    def test_payment_link(self):
        uuid = self.create()["uuid"]
        receipt = {
            "total": 100,
            "items": [{
                "Pizza": 90
            }]
        }
        self.assertResponse(0, apiclient.update_transaction(uuid, receipt=receipt))
        transaction = apiclient.get_transaction(uuid)["transaction"]

        hashmark = urllib.parse.parse_qs(urllib.parse.urlparse(transaction["payment_url"])[5])
        print(hashmark)

        transaction_hashmark = hashmark["transaction"] if "transaction" in hashmark else hashmark["?transaction"]
        token_hashmark = hashmark["token"] if "token" in hashmark else hashmark["?token"]

        self.assertEqual(transaction["uuid"], transaction_hashmark[0])
        self.assertTrue("host" in hashmark or "?host" in hashmark)

        rsp = apiclient.send_api_request("GET", ["core", "transaction", transaction["uuid"]], token=token_hashmark[0])
        self.assertResponse(0, rsp)
        self.assertEqual(200, requests.get(transaction["payment_url"]).status_code)

    def test_create(self):
        #TODO test status is valid
        uuid1 = self.create()["uuid"]

        self.assertResponse(0, apiclient.get_transaction(uuid1))

    def test_retreive(self):
        uuid = self.create()["uuid"]
        transaction = apiclient.get_transaction(uuid)
        expected = {
            "result": 0,
            "transaction": {
                "uuid": uuid,
                "version": transaction["transaction"]["version"],
                "customer_platform_type": "sms",
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
       apiclient.update_transaction(transaction_uuid, status="completed")
       self.assertEqual("completed", apiclient.get_transaction(transaction_uuid)["transaction"]["status"])
       # TODO what happens when an invalid status is sent


    def test_update_delegator(self):
        #TODO what happens when an invalid delegator_uuid is sent
       transaction_uuid = self.create()["uuid"]
       apiclient.update_transaction(transaction_uuid, delegator_uuid=self.delegator_uuid)
       transaction = apiclient.get_transaction(transaction_uuid)["transaction"]
       self.assertEqual(self.delegator_uuid, transaction["delegator_uuid"])

    def test_send_message(self):
        transaction_uuid = self.create()["uuid"]
        self.assertResponse(0, apiclient.send_message(transaction_uuid, from_customer=True, content="test1"))
        messages = apiclient.get_transaction(transaction_uuid)["transaction"]["messages"]
        expected = [{
            "type": "text",
            "content": "test1",
            "from_customer": True,
            "timestamp": messages[0]["timestamp"]
        }]
        apiclient.send_message(transaction_uuid, from_customer=False, content="test2")
        messages = apiclient.get_transaction(transaction_uuid)["transaction"]["messages"]
        expected.append({
            "type": "text",
            "content": "test2",
            "from_customer": False,
            "timestamp": messages[1]["timestamp"]
        })
        self.assertResponse(19, apiclient.send_message(transaction_uuid,
                from_customer=False, content="test3", mtype="asdf"))
