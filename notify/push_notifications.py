import boto.sns
import json

SNS_ACCESS_KEY = None
SNS_SECRET_KEY = None
REGION = None
PLATFORM_ENDPOINT_ARN = None

def _load_config():
    with open("config.json", "r") as f:
        sns_config = json.loads(f.read())["sns"]
        SNS_ACCESS_KEY = sns_config["access_key"]
        SNS_SECRET_KEY = sns_config["secret_key"]
        REGION = sns_config["region"]
        PLATFORM_ENDPOINT_ARN = sns_config["platform_endpoint_arn"]

_load_config()

# Initialize the sns connection
sns_conn = boto.sns.connect_to_region(
    REGION,
    aws_access_key_id=SNS_ACCESS_KEY,
    aws_secret_access_key=SNS_SECRET_KEY,
)

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

    push_endpoint_arn = new_item["push_endpoint_arn"]["S"]
    send_push_notifications(push_endpoint_arn, new_last_message["content"]["S"])

# Sends a push notification using boto's SNS
def send_push_notifications(push_endpoint_arn, message):
    publish_result = sns_conn.publish(
        target_arn=push_endpoint_arn,
        message=message,
    )

    print (publish_result)
