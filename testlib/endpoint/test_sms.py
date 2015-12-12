import nose
from gator import apiclient
from endpoint.rest import RestTest

class NotifyTest(RestTest):

    def setUp(self):
        apiclient.clear_database()

    def test_handle_sms(self):
        delegator_uuid = apiclient.create_delegator("", "", "15555555552", "noreply@gmail.com", "1", "")["uuid"]
        self.assertResponse(0, apiclient.send_sms_to_api("15555555551", "hello"))
        transaction_uuid = apiclient.assign_new_transaction(delegator_uuid)["transaction_uuid"]
        transaction = apiclient.get_transaction(transaction_uuid)["transaction"]
        customer = apiclient.get_customer(transaction["customer_uuid"])["customer"]
        delegator = apiclient.get_delegator(delegator_uuid)["delegator"]

        self.assertEqual(1, len(transaction["messages"]))
        self.assertEqual("sms", transaction["customer_platform_type"])
        self.assertEqual("hello", transaction["messages"][0]["content"])
        self.assertEqual("15555555551", customer["phone_number"])
        self.assertTrue(transaction_uuid in customer["active_transaction_uuids"])
        self.assertTrue(transaction_uuid in delegator["active_transaction_uuids"])

        self.assertResponse(0, apiclient.send_sms_to_api("15555555551", "second msg"))
        transaction = apiclient.get_transaction(transaction_uuid)["transaction"]

        self.assertEqual(2, len(transaction["messages"]))
        self.assertEqual("second msg", transaction["messages"][1]["content"])

        self.assertResponse(0, apiclient.update_transaction(transaction_uuid, status="completed"))
        self.assertResponse(0, apiclient.send_sms_to_api("15555555551", "new transaction"))

        self.assertResponse(0, apiclient.assign_new_transaction(delegator_uuid))


if __name__ == "__main__":
    nose.main(defaultTest=__name__)
