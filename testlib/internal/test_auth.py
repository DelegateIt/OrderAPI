import nose
import unittest
import base64

import gator.apiclient as apiclient

from gator.core.auth import login_facebook, validate_token, UuidType, validate_permission, Permission
from gator.core.common import GatorException, Errors

class AuthTest(unittest.TestCase):

    def setUp(self):
        apiclient.clear_database()
        self.customer_fbuser_id = "1"
        self.customer_uuid = apiclient.create_customer("name", "name", "15555555551", "1", "")["uuid"]
        fb = {"fbuser_id": self.customer_fbuser_id, "fbuser_token": "12313123sffsdf"}
        apiclient.update_customer(self.customer_uuid, fb)
        self.delegator_fbuser_id = "2"
        self.delegator_uuid = apiclient.create_delegator("asdf", "dsfsd", "15555555552",
                "noreply@gmail.com", self.delegator_fbuser_id, "")["uuid"]

    def assertException(self, exception, func):
        try:
            func()
        except exception as e:
            self.assertTrue(True)
        else:
            self.assertTrue(False, "An exception was expected")

    def test_token_validation(self):
        login = login_facebook("sfsdf", self.customer_fbuser_id, UuidType.CUSTOMER)
        self.assertEqual(self.customer_uuid, login[0])
        token = login[1]
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
        customer_token = login_facebook("sfsdf", self.customer_fbuser_id, UuidType.CUSTOMER)[1]
        customer_identity = validate_token(customer_token)
        delegator_token = login_facebook("asfdd", self.delegator_fbuser_id, UuidType.DELEGATOR)[1]
        delegator_identity = validate_token(delegator_token)

        validate_permission(delegator_identity, [Permission.ALL_DELEGATORS])
        validate_permission(delegator_identity, [Permission.DELEGATOR_OWNER], self.delegator_uuid)
        self.assertException(GatorException,
                lambda: validate_permission(delegator_identity, [Permission.DELEGATOR_OWNER], "123123132"))
        self.assertException(GatorException,
                lambda: validate_permission(customer_identity, [Permission.ALL_DELEGATORS]))
        validate_permission(customer_identity, [Permission.CUSTOMER_OWNER], customer_identity[0])
        self.assertException(GatorException,
                lambda: validate_permission(customer_identity, [Permission.CUSTOMER_OWNER], "12313123123"))
        self.assertException(GatorException,
                lambda: validate_permission(customer_identity, [Permission.DELEGATOR_OWNER], customer_identity[0]))
