import nose
from gator import apiclient
from endpoint.rest import RestTest

class NotifyTest(RestTest):

    def setUp(self):
        apiclient.clear_database()

    def test_handle_sms(self):
        delegator_uuid = apiclient.create_delegator("1", "2", "15555555552", "noreply@gmail.com", "1", "2")["uuid"]
        self.assertResponse(0, apiclient.send_sms_to_api("15555555551", "hello"))
        transaction_uuid = apiclient.assign_new_transaction(delegator_uuid)["transaction_uuid"]
        transaction = apiclient.get_transaction(transaction_uuid)["transaction"]
        customer = apiclient.get_customer(transaction["customer_uuid"])["customer"]
        delegator = apiclient.get_delegator(delegator_uuid)["delegator"]

        self.assertEqual(1, len(transaction["messages"]))
        self.assertEqual("sms", transaction["customer_platform_type"])
        self.assertEqual("hello", transaction["messages"][0]["content"])
        self.assertEqual("15555555551", customer["phone_number"])
        self.assertEqual(delegator_uuid, transaction["delegator_uuid"])

        self.assertResponse(0, apiclient.send_sms_to_api("15555555551", "second msg"))
        transaction = apiclient.get_transaction(transaction_uuid)["transaction"]

        self.assertEqual(2, len(transaction["messages"]))
        self.assertEqual("second msg", transaction["messages"][1]["content"])
        self.assertEqual("text", transaction["messages"][1]["type"])

        self.assertResponse(0, apiclient.update_transaction(transaction_uuid, status="completed"))
        self.assertResponse(0, apiclient.send_sms_to_api("15555555551", "new transaction"))

        self.assertResponse(0, apiclient.assign_new_transaction(delegator_uuid))

    def test_open_sms(self):
        phone = "15555550000"
        delegator_uuid = apiclient.create_delegator("A", "M", "15555550001", "noreply@gmail.com", "1", "")["uuid"]
        transaction_uuid = apiclient.open_sms_order(phone, delegator_uuid)["transaction_uuid"]
        customer_uuid = apiclient.get_transaction(transaction_uuid)["transaction"]["customer_uuid"]
        trans_list = apiclient.list_delegators_transactions(delegator_uuid)["transactions"]
        self.assertEqual(trans_list[0]["uuid"], transaction_uuid)
        self.assertResponse(0, apiclient.send_sms_to_api(phone, "hello"))
        self.assertEqual(1, len(apiclient.list_delegators_transactions(delegator_uuid)["transactions"]))
        self.assertResponse(25, apiclient.open_sms_order(phone, delegator_uuid))
        self.assertResponse(25, apiclient.open_sms_order(phone, delegator_uuid))
        self.assertResponse(0, apiclient.update_transaction(transaction_uuid, status="completed"))
        self.assertResponse(0, apiclient.create_transaction(customer_uuid, "sms"))

    def test_help_message(self):
        delegator_uuid = apiclient.create_delegator("1", "2", "15555555552", "noreply@gmail.com", "1", "2")["uuid"]

        for message in ["HELP", "  HELP ", "Help", "help", "  HelP"]:
            self.assertResponse(0, apiclient.send_sms_to_api("15555555551", message))
            self.assertResponse(8, apiclient.assign_new_transaction(delegator_uuid))

    def test_multiple_transactions_handle_sms(self):
        pass # Need to fill this in later

if __name__ == "__main__":
    nose.main(defaultTest=__name__)
