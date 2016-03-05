import unittest
import nose

#################################################
# BLACK MAGIC THAT MOCKS THE SNS SERIVCE OBJECT #
#    MUST BE IMPORTED BEFORE EVERYTHING ELSE    #
#################################################

class MockSNSService(object):
    def __init__(self):
        self.last_created_token = None
        self.last_deleted_token = None

    def create_platform_endpoint(self, platform_application_arn, token):
        """
            Returns the device token as the endpoint ARN for easier testing.
        """
        self.last_created_token = token
        return {'CreatePlatformEndpointResponse':
                    {'CreatePlatformEndpointResult':
                    {'EndpointArn': token}}}

    def delete_endpoint(self, endpoint_arn):
        self.last_deleted_token = endpoint_arn

import gator.core.service as service
service.sns = MockSNSService()

#################
# Other Imports #
#################

import gator.core.push_endpoints as push
import gator.apiclient as apiclient

from gator.core.models import Customer, CFields, push_endpoints

BENS_PHONE_ARN = "EB0144965D9916B274BDCC2AEDD5D5DD9D1DF1FEE59F07C7EDAD292D1F81DC61"

class TestPush(unittest.TestCase):
    def setUp(self):
        apiclient.clear_database()

        self.customer = Customer.create_new()
        self.customer.create()

    def test_push_wholistic(self):
        # Create the initial push endpoint
        push.create_push_endpoint(self.customer, BENS_PHONE_ARN)

        # Make sure DB info is correct
        item = [item for item in push_endpoints.scan()][0]
        self.assertEquals(item["device_id"], BENS_PHONE_ARN)
        self.assertEquals(item["customer_uuid"], self.customer[CFields.UUID])
        self.assertEquals(item["endpoint_arn"], BENS_PHONE_ARN)

        # Make sure that SNS was usee correctly
        self.assertEquals(service.sns.last_created_token, BENS_PHONE_ARN)
        self.assertIsNone(service.sns.last_deleted_token)

        # Recreate it push endpoint
        self.customer = Customer.create_new()
        self.customer.create()
        push.create_push_endpoint(self.customer, BENS_PHONE_ARN)

        # Make sure that the DB info is correct, again
        item = [item for item in push_endpoints.scan()][0]
        self.assertEquals(item["device_id"], BENS_PHONE_ARN)
        self.assertEquals(item["customer_uuid"], self.customer[CFields.UUID])
        self.assertEquals(item["endpoint_arn"], BENS_PHONE_ARN)

        # Make sure that SNS was usee correctly, again
        self.assertEquals(service.sns.last_created_token, BENS_PHONE_ARN)
        self.assertEquals(service.sns.last_deleted_token, BENS_PHONE_ARN)
