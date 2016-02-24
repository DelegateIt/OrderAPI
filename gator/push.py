from boto.dynamodb2.exceptions import ItemNotFound

import gator.config as config

from gator.service import sns
from gator.models import CFields, push_endpoints
from gator.common import GatorException, Errors

PLATFORM_ENDPOINT_ARN = config.store["sns"]["platform_endpoint_arn"]

def create_push_endpoint(customer, device_id):
    try:
        # Remove old device_id from push_endpoints and delete the endpoint_arn
        item = push_endpoints.get_item(device_id=device_id, consistent=True)
        remove_endpoint(item["endpoint_arn"])
    except ItemNotFound:
        pass

    # Create a new item if none exists
    endpoint_arn = create_endpoint(device_id)

    push_endpoints.put_item(data={
            "device_id": device_id,
            "customer_uuid": customer[CFields.UUID],
            "endpoint_arn": endpoint_arn},
        overwrite=True)

def create_endpoint(device_id):
    try:
        resp = sns.create_platform_endpoint(
            platform_application_arn=PLATFORM_ENDPOINT_ARN,
            token=device_id
        )

        return resp["CreatePlatformEndpointResponse"]\
                   ['CreatePlatformEndpointResult']\
                   ['EndpointArn']
    except:
        raise GatorException(Errors.SNS_FAILURE)

def remove_endpoint(endpoint_arn):
    try:
        sns.delete_endpoint(endpoint_arn=endpoint_arn)
    except:
        raise GatorException(Errors.SNS_FAILURE)
