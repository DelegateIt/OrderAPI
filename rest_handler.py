from flask import Flask, request

import time
import json

import models
import common

from models import Customer, Message, Delegator, Transaction
from common import Errors, TransactionStatus

app = Flask(__name__)
app.debug = True

VALID_PLATFORMS = ["sms"]

@app.route('/')
def index():
    return "GatorRestService is up and running!"

@app.route('/customer/<phone_number>', methods=['POST', 'GET'])
def customer(phone_number):
    if request.method == 'POST':
        if models.customers.has_item(phone_number=phone_number, consistent=True):
            return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

        data_dict = json.loads(request.data)

        if not verify_dict_contains_keys(data_dict, ["first_name", "last_name"]):
            return common.error_to_json(Errors.DATA_NOT_PRESENT)

        customer = Customer(first_name=data_dict["first_name"], last_name=data_dict["last_name"], phone_number=phone_number)
        models.customers.put_item(data=customer.get_data())

        return json.dumps({"result": 0})
    elif request.method == 'GET':
        if not models.customers.has_item(phone_number=phone_number, consistent=True):
            return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

        customer = models.customers.get_item(phone_number=phone_number, consistent=True)

        return json.dumps({
                "result": 0,
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

    if not models.customers.has_item(phone_number=phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    message = Message(content=data_dict["content"])
    customer = models.customers.get_item(phone_number=phone_number, consistent=True)

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
    if not models.customers.has_item(phone_number=phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = models.customers.get_item(phone_number=phone_number, consistent=True)

    return convert_messages_to_json(customer["messages"])

@app.route('/get_messages_past_timestamp/<phone_number>/<timestamp>', methods=['GET'])
def get_messages_past_timestamp(phone_number, timestamp):
    if not models.customers.has_item(phone_number=phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    messages = models.customers.get_item(phone_number=phone_number, consistent=True)["messages"]
    timestamp = int(timestamp)

    return convert_messages_to_json([message for message in messages if int(message["timestamp"]) > timestamp])

@app.route('/transaction/<customer_phone_number>', methods=['GET', 'POST'])
def transaction(customer_phone_number):
    if not models.customers.has_item(phone_number=customer_phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    if request.method == 'POST':
        data_dict = json.loads(request.data)

        transaction = Transaction(
                customer_phone_number = customer_phone_number,
                status = TransactionStatus.STARTED if not data_dict.has_key("status") else data_dict["status"],
                delegator_phone_number =  data_dict["delegator_phone_number"] if data_dict.has_key("delegator_phone_number") else None)

        models.transactions.put_item(data=transaction.get_data())

        return json.dumps({"result": 0})
    elif request.method == 'GET':
        transaction = models.transactions.get_item(customer_phone_number=customer_phone_number, consistent=True)

        return json.dumps({
            "result": 0,
            "customer_phone_number": transaction["customer_phone_number"],
            "status": int(transaction["status"]),
            "delegator_phone_number": transaction["delegator_phone_number"]})

@app.route('/change_transaction_status/<phone_number>')
def change_transaction_status(phone_number):
    pass

####################
# Helper functions #
####################

def verify_dict_contains_keys(dic, keys):
    for cur_key in dic:
        if cur_key not in keys:
            return False

    return True

def convert_messages_to_json(messages):
    if messages is None:
        return json.dumps({"result": 0, "messages": None})

    return json.dumps({
        "result": 0,
        "messages": [{
            "content": message["content"],
            "timestamp": int(message["timestamp"])} for message in messages]})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
