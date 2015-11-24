import nose
from gator import apiclient
from endpoint.rest import RestTest

class CustomerTest(RestTest):
    def setUp(self):
        apiclient.clear_database()

    def create(self):
        #TODO test empty names and bad phone numbers
        #TODO test for uniqueness in customers
        self.fbuser_id = "1111"
        rsp = apiclient.create_customer("firstname", "lastname", "15555555551", self.fbuser_id, "")
        self.assertResponse(0, rsp)
        return rsp

    def test_create(self):
        rsp = self.create()
        self.assertResponse(0, apiclient.get_customer(rsp["uuid"]))

    def test_retreive(self):
        self.assertResponse(10, apiclient.get_customer("fake uuid"))
        uuid = self.create()["uuid"]
        rsp = apiclient.get_customer(uuid)
        self.assertResponse(0, rsp)
        self.assertEqual("firstname", rsp["customer"]["first_name"])
        self.assertEqual("lastname", rsp["customer"]["last_name"])
        self.assertEqual("15555555551", rsp["customer"]["phone_number"])
        self.assertEqual(uuid, rsp["customer"]["uuid"])

    def test_uniqueness(self):
        self.create()
        self.assertResponse(2, apiclient.create_customer("slkdfjsk", "sldkfj", "15555555551"))
        self.assertResponse(2, apiclient.create_customer("slkdfjsk", "sldkfj", "15555555552",
                fbuser_id=self.fbuser_id, fbuser_token=""))

    def test_update(self):
        #TODO test bad email and phone numbers and empty names
        #TODO test stripping out special chars in name
        uuid = self.create()["uuid"]
        update = {
            "first_name": "newfirst",
            "last_name": "newlast",
            "email": "noreply@gmail.com",
            "phone_number": "15555555551"
        }
        update_rsp = apiclient.update_customer(uuid, update)
        self.assertResponse(0, update_rsp)
        get_rsp = apiclient.get_customer(uuid)["customer"]
        for key in update:
            self.assertEqual(update[key], get_rsp[key])

        self.assertResponse(10, apiclient.update_customer("fake uuid", update))

    def test_login(self):
        uuid = self.create()["uuid"]
        rsp = apiclient.fb_login_customer(self.fbuser_id, "")
        self.assertResponse(10, apiclient.fb_login_customer("12312313123", ""))
        self.assertResponse(0, rsp)
        self.assertEquals(uuid, rsp["customer"]["uuid"])
        rsp_get = apiclient.send_api_request("GET", ["core", "customer", uuid], token=rsp["token"])
        self.assertResponse(0, rsp_get)
        rsp_get = apiclient.send_api_request("GET", ["core", "customer", "123123213"], token=rsp["token"])
        self.assertResponse(14, rsp_get)
        rsp_get = apiclient.send_api_request("GET", ["core", "customer", uuid], token=None)
        self.assertResponse(12, rsp_get)

