import nose
from gator import apiclient
from endpoint.rest import RestTest

class DelegatorTest(RestTest):

    def setUp(self):
        apiclient.clear_database()

    def create(self):
        #TODO test empty names and bad phone numbers and bad emails
        self.fbuser_id = "1111"
        rsp = apiclient.create_delegator("firstname", "lastname", "15555555555", "noreply@gmail.com",
                self.fbuser_id, "sdfd")
        self.assertResponse(0, rsp)
        return rsp

    def test_create(self):
        rsp = self.create()
        self.assertResponse(0, apiclient.get_delegator(rsp["uuid"]))

    def test_retreive(self):
        self.assertResponse(9, apiclient.get_delegator("fake uuid"))
        uuid = self.create()["uuid"]
        rsp = apiclient.get_delegator(uuid)
        self.assertResponse(0, rsp)
        rsp = rsp["delegator"]
        self.assertEqual("firstname", rsp["first_name"])
        self.assertEqual("lastname", rsp["last_name"])
        self.assertEqual("15555555555", rsp["phone_number"])
        self.assertEqual("noreply@gmail.com", rsp["email"])
        self.assertEqual(uuid, rsp["uuid"])

    def test_update(self):
        #TODO test bad email and phone numbers and empty names
        #TODO test stripping out special chars in name
        uuid = self.create()["uuid"]
        update = {
            "first_name": "newfirst",
            "last_name": "newlast",
            "email": "no.....reply@gmail.com",
            "phone_number": "15555555551"
        }
        update_rsp = apiclient.update_delegator(uuid, update)
        self.assertResponse(0, update_rsp)
        get_rsp = apiclient.get_delegator(uuid)["delegator"]
        for key in update:
            self.assertEqual(update[key], get_rsp[key])

        self.assertResponse(9, apiclient.update_delegator("fake uuid", update))

    def test_uniqueness(self):
        self.create()
        self.assertResponse(4, apiclient.create_delegator("slkdfjsk", "sldkfj", "15555555555",
                "no.reply@gmail.com", fbuser_id="212313", fbuser_token=""))
        self.assertResponse(4, apiclient.create_delegator("slkdfjsk", "sldkfj", "15555555551",
                "noreply@gmail.com", fbuser_id="212313", fbuser_token=""))
        self.assertResponse(4, apiclient.create_delegator("slkdfjsk", "sldkfj", "15555555552",
                "no..reply@gmail.com", fbuser_id=self.fbuser_id, fbuser_token=""))

    def test_get_list(self):
        uuids = [
            self.create()["uuid"],
            apiclient.create_delegator("a", "b", "15555555551", "no..reply@gmail.com", "1", "")["uuid"]
        ]
        dlgt_list = apiclient.get_delegator_list()
        self.assertResponse(0, dlgt_list)
        for dlgt in dlgt_list["delegators"]:
            uuids.remove(dlgt["uuid"])
        self.assertEqual(len(uuids), 0, "get_delegator_list returned a bad response")

    def test_login(self):
        uuid = self.create()["uuid"]
        rsp = apiclient.fb_login_delegator(self.fbuser_id, "")
        self.assertResponse(0, rsp)
        self.assertEquals(uuid, rsp["delegator"]["uuid"])
        rsp_get = apiclient.send_api_request("GET", ["core", "delegator", uuid], token=rsp["token"])
        self.assertResponse(0, rsp_get)
        rsp_get = apiclient.send_api_request("GET", ["core", "delegator", uuid], token=None)
        self.assertResponse(12, rsp_get)

    def test_assign_transaction(self):
        customer_uuid = apiclient.create_customer("asf", "asdf", "15555555551")["uuid"]
        delegator_uuid = self.create()["uuid"]
        self.assertResponse(8, apiclient.assign_new_transaction(delegator_uuid))
        transaction_uuid = apiclient.create_transaction(customer_uuid)["uuid"]
        rsp = apiclient.assign_new_transaction(delegator_uuid)
        self.assertResponse(0, rsp)
        self.assertEqual(transaction_uuid, rsp["transaction_uuid"])
        self.assertTrue(transaction_uuid in apiclient.get_delegator(delegator_uuid)["delegator"]["active_transaction_uuids"])

