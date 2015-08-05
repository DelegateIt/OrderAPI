from flask import Flask, request

import time
import json

import models
import common

from models import Customer, Message
from common import Errors

app = Flask(__name__)
app.debug = True

VALID_PLATFORMS = ["sms"]

@app.route('/')
def index():
    return "GatorRestService is up and running!"

@app.route('/customer/<phone_number>', methods=['POST', 'GET'])
def customer(phone_number):
    if request.method == 'POST':
        if models.customers.has_item(phone_number=phone_number):
            return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

        data_dict = json.loads(request.data)

        if not verify_dict_contains_keys(data_dict, ["first_name", "last_name"]):
            return common.error_to_json(Errors.DATA_NOT_PRESENT)

        customer = Customer(first_name=data_dict["first_name"], last_name=data_dict["last_name"], phone_number=phone_number)
        models.customers.put_item(data=customer.get_data())

        return json.dumps({"result": 0})
    elif request.method == 'GET':
        if not models.customers.has_item(phone_number=phone_number):
            return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

        customer = models.customers.get_item(phone_number=phone_number)

        return json.dumps({
                "first_name":   customer["first_name"],
                "last_name":    customer["last_name"],
                "phone_number": customer["phone_number"]})

@app.route('/send_message/<phone_number>', methods=['POST'])
def send_message(phone_number):
    data_dict = json.loads(request.data)

    if not verify_dict_contains_keys(data_dict, ["content", "platform_type"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    elif data_dict["platform_type"] not in VALID_PLATFORMS:
        return common.error_to_json(Errors.UNSUPPORTED_PLATFORM)

    if not models.customers.has_item(phone_number=phone_number):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    message = Message(data_dict["content"])
    customer = models.customers.get_item(phone_number=phone_number)

    if customer["messages"] is None:
        customer["messages"] = []

    customer["messages"].append(message.get_data())

    # Save data to the database
    customer.save()

    return json.dumps({
            "result": 0,
            "timestamp": message.timestamp
        })

@app.route('/get_messages/<phone_number>', methods=['GET'])
def get_messages(phone_number):
    if not models.customers.has_item(phone_number=phone_number):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = models.customers.get_item(phone_number=phone_number)

    if customer["messages"] == None:
        return json.dumps(None)
    else:
        return convert_messages_to_json(customer["messages"])

@app.route('/get_messages_past_timestamp/<phone_number>/<timestamp>', methods=['GET'])
def get_messages_past_timestamp(phone_number, timestamp):
    if not models.customers.has_item(phone_number=phone_number):
        return common.error_to_json(Errors.USER_DOES_NOT_EXIST)

    messages = models.customers.get_item(phone_number=phone_number)["messages"]
    timestamp = int(timestamp)

    return convert_messages_to_json([message for message in messages if int(message["timestamp"]) > timestamp])


@app.route('/transaction/<phone_number>')
def mark_transaction_started(phone_number):
    session = models.Session(bind=models.engine)

    if phone_number in message_store:
        user_data = message_store[phone_number]
    else:
        return json.dumps({"success": False})

    with transaction_lock:
        user_data["transaction_status"] = TRANSACTION_STARTED

    return json.dumps({"success": True})

####################
# Helper functions #
####################

def verify_dict_contains_keys(dic, keys):
    for cur_key in dic:
        if cur_key not in keys:
            return False

    return True

def convert_messages_to_json(messages):
    return json.dumps([{"content": message["content"], "timestamp": int(message["timestamp"])}
        for message in messages])

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True, threaded=True)
