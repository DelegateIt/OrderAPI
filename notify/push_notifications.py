import json
import urllib2

config_file = open("./push_config.json", "r")
config = json.loads(config_file.read())

BASE_URL = config["base_url"]
SEND_PUSH_NOTIFICATION_ENDPOINT = "%s/push/send_push_notification/" % BASE_URL

# Handles dynamodb event stream request
def handler(event, context):
    new_item = event["Records"][0]["dynamodb"]["NewImage"]
    old_item = event["Records"][0]["dynamodb"]["OldImage"]

    # Important/Required fields
    platform_type = new_item["customer_platform_type"]["S"]
    new_last_message = new_item["messages"]["L"][-1]["M"]
    from_delegator = new_last_message["from_customer"]["BOOL"] == "false"
    old_last_message = old_item["messages"]["L"][-1]["M"]

    # Return if the platform isn't ios, the last message was sent by the
    # customer, or the transaction update didn't include a new message
    if platform_type != "ios" or not from_delegator or new_last_message == old_last_message:
        return

    # Request data
    customer_uuid = new_item["customer_uuid"]["S"]
    message = new_last_message["content"]["S"]

    req = urllib2.Request(
        "%s%s" % (SEND_PUSH_NOTIFICATION_ENDPOINT, "10535386475720166119"),
        json.dumps({"message": message}),
        {"Content-Type": "application/json"})

    f = urllib2.urlopen(req)
    f.close()
