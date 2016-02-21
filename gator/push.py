import gator.config as config

from gator.service import sns
from gator.models import CFields, push_endpoints
from gator.common import GatorException, Errors

PLATFORM_ENDPOINT_ARN = config.store["sns"]["platform_endpoint_arn"]

def create_push_endpoint(customer, device_id):
    # Remove old device_id from push_endpoints and delete the endpoint_arn
    item = push_endpoints.get_item(device_id, consistent=True)
    if item is not None:
        remove_platform_endpoint(item["device_id"])
        item.delete()

    endpoint_arn = create_platform_endpoint(device_id)

    push_endpoints.put_item(data={
        "device_id": device_id,
        "customer_uuid": customer[CFields.UUID],
        "platform_endpoint_arn": endpoint_arn})

def create_platform_endpoint(device_id):
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

def remove_platform_endpoint(device_id):
    try:
        resp = sns.delete_endpoint(
           platform_application_arn=PLATFORM_ENDPOINT_ARN,
           token=device_id
        )
    except:
        raise GatorException(Errors.SNS_FAILURE)
