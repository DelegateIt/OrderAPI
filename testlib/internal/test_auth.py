#!/usr/bin/env python3

import nose
import unittest
import base64

from gator.auth import login_facebook, validate_token, UuidType, validate_permission, Permission
from gator.common import GatorException, Errors
from gator import apiclient

class AuthTest(unittest.TestCase):

    def setUp(self):
        apiclient.clear_database()
        self.customer_fbuser_id = "1"
        self.customer_uuid = apiclient.create_customer("name", "name", "15555555551")["uuid"]
        fb = {"fbuser_id": self.customer_fbuser_id, "fbuser_token": "12313123sffsdf"}
        apiclient.update_customer(self.customer_uuid, fb)

    def assertException(self, exception, func):
        try:
            func()
        except exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False, "An exception was expected")

    def test_token_validation(self):
        token = login_facebook("sfsdf", self.customer_fbuser_id, UuidType.CUSTOMER)[1]
        validate_token(token)

        #modify the token so it fails validation
        token = base64.b64encode(bytes([1, 2, 3]) + base64.b64decode(token.encode("utf-8"))).decode("utf-8")
        try:
            validate_token(token)
        except GatorException as e:
            self.assertEquals(e.error_type.returncode, Errors.INVALID_TOKEN.returncode)
        else:
            self.assertTrue(False, "The token validation should haved failed")

    def test_permission(self):
        token = login_facebook("sfsdf", self.customer_fbuser_id, UuidType.CUSTOMER)[1]
        identity = validate_token(token)
        self.assertException(GatorException,
                lambda: validate_permission(identity, [Permission.ALL_DELEGATORS]))
        validate_permission(identity, [Permission.CUSTOMER_OWNER], identity[0])
        self.assertException(GatorException,
                lambda: validate_permission(identity, [Permission.CUSTOMER_OWNER], "12313123123"))

if __name__ == "__main__":
    nose.main(defaultTest=__name__)
