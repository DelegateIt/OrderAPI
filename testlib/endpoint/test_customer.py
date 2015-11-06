#!/usr/bin/env python3

import nose
import unittest
from gator import apiclient
from endpoint.rest import RestTest

class CustomerTest(RestTest):

    def setUp(self):
        apiclient.clear_database()

    def create(self):
        #TODO test empty names and bad phone numbers
        #TODO test for uniqueness in customers
        rsp = apiclient.create_customer("firstname", "lastname", "15016586868")
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
        self.assertEqual("firstname", rsp["first_name"])
        self.assertEqual("lastname", rsp["last_name"])
        self.assertEqual("15016586868", rsp["phone_number"])
        self.assertEqual(uuid, rsp["uuid"])

    def test_uniqueness(self):
        self.create()
        self.assertResponse(2, apiclient.create_customer("slkdfjsk", "sldkfj", "15016586868"))

    def test_update(self):
        #TODO test bad email and phone numbers and empty names
        #TODO test stripping out special chars in name
        uuid = self.create()["uuid"]
        update = {
            "first_name": "newfirst",
            "last_name": "newlast",
            "email": "noreply@gmail.com",
            "phone_number": "15016586868"
        }
        update_rsp = apiclient.update_customer(uuid, update)
        self.assertResponse(0, update_rsp)
        get_rsp = apiclient.get_customer(uuid)
        for key in update:
            self.assertEqual(update[key], get_rsp[key])

        self.assertResponse(10, apiclient.update_customer("fake uuid", update))

if __name__ == "__main__":
    nose.main(defaultTest=__name__)
