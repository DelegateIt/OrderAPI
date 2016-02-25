import request

BASE_URL = "api.godelegateit.com"
SEND_PUSH_NOTIFICATION_ENDPOINT = "%s/push/send_push_notification/" % BASE_URL

# Handles dynamodb event stream request
def handler(event, context):
    new_item = event["Records"][0]["dynamodb"]["NewImage"]
    old_item = event["Records"][0]["dynamodb"]["OldImage"]

    # Important/Required fields
    platform_type = new_item["platform_type"]["customer_platform_type"]["S"]
    new_last_message = new_item["messages"]["L"][-1]
    from_delegator = new_last_message["from_customer"] == "false"
    old_last_message = old_item["messages"]["L"][-1]

    # Return if the platform isn't ios, the last message was sent by the
    # customer, or the transaction update didn't include a new message
    if platform_type != "ios" or not from_delegator or new_last_message == old_last_message:
        return

    # Request data
    customer_uuid = new_item["customer_uuid"]["S"]
    message = new_last_message["content"]["S"]

    request.post("%s%s" % (SEND_PUSH_NOTIFICATION_ENDPOINT, customer_uuid),
        data={"message": message})
