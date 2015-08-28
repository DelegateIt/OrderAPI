#!/usr/bin/env python3

from flask import Flask, request

import time
import argparse
import jsonpickle
import json
import sys

import models
import common

from models import Customer, Message, Delegator, Transaction
from common import Errors, TransactionStatus

app = Flask(__name__)
app.debug = True

@app.after_request
def after_request(response):
    #TODO - Important Security - replace '*' with name of the server hosting the delegator web client
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

@app.route('/')
def index():
    return "GatorRestService is up and running!"

@app.route('/customer', methods=['POST'])
def create_customer():
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not verify_dict_contains_keys(data_dict, ["phone_number"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    customer = None
    if verify_dict_contains_keys(data_dict, ["first_name", "last_name"]):
        customer = Customer(
            phone_number=data_dict["phone_number"],
            first_name=data_dict["first_name"],
            last_name=data_dict["last_name"])
    else:
        customer = Customer(phone_number=data_dict["phone_number"])

    if not customer.is_unique():
        return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

    models.customers.put_item(data=customer.get_data())

    return jsonpickle.encode({"result": 0, "uuid": customer.uuid}, unpicklable=False)

@app.route('/customer/<uuid>', methods=['GET'])
def customer(uuid):
    if not models.customers.has_item(uuid=uuid, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = models.customers.get_item(uuid=uuid, consistent=True)

    to_return = {"result": 0}
    to_return.update(customer._data)
    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/delegator', methods=['POST'])
def create_delegator():
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not verify_dict_contains_keys(data_dict, ["phone_number", "email", "first_name", "last_name"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    delegator = Delegator(
            first_name=data_dict["first_name"],
            last_name=data_dict["last_name"],
            phone_number=data_dict["phone_number"],
            email=data_dict["email"])

    if not delegator.is_unique():
        return common.error_to_json(Errors.DELEGATOR_ALREADY_EXISTS)

    models.delegators.put_item(data=delegator.get_data())

    return jsonpickle.encode({"result": 0, "uuid": delegator.uuid}, unpicklable=False)

@app.route('/delegator/<uuid>', methods=['GET', 'PUT'])
def delegator(uuid):
    if not models.delegators.has_item(uuid=uuid, consistent=True):
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    delegator = models.delegators.get_item(uuid=uuid, consistent=True)

    to_return = {"result": 0}
    to_return.update(delegator._data)
    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/send_message/<transaction_uuid>', methods=['POST'])
def send_message(transaction_uuid):
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not verify_dict_contains_keys(data_dict, ["from_customer", "content", "platform_type"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    if not models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = models.transactions.get_item(uuid=transaction_uuid)

    message = Message(
        from_customer=data_dict["from_customer"],
        content=data_dict["content"],
        platform_type=data_dict["platform_type"])

    if transaction["messages"] is None:
        transaction["messages"] = []

    transaction["messages"].append(message.get_data())

    # Save data to the database
    transaction.save()

    return jsonpickle.encode({
            "result": 0,
            "timestamp": message.timestamp
        }, unpicklable=False)

@app.route('/get_messages/<transaction_uuid>', methods=['GET'])
def get_messages(transaction_uuid):
    if not models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = models.transactions.get_item(uuid=transaction_uuid, consistent=True)

    to_return = {"result": 0}

    if transaction["messages"] is not None:
        to_return.update({"messages": [message for message in transaction["messages"]]})
    else:
        to_return.update({"messages": None})

    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/get_messages_past_timestamp/<transaction_uuid>/<timestamp>', methods=['GET'])
def get_messages_past_timestamp(transaction_uuid, timestamp):
    if not models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    messages = models.transactions.get_item(uuid=transaction_uuid, consistent=True)["messages"]
    timestamp = int(timestamp)

    to_return = {"result": 0}

    if messages is not None:
        to_return.update({"messages": [message for message in messages
            if int(message["timestamp"]) > timestamp]})
    else:
        to_return.update({"messages": None})

    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/transaction', methods=['POST'])
def create_transaction():
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not verify_dict_contains_keys(data_dict, ["customer_uuid"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    if not models.customers.has_item(uuid=data_dict["customer_uuid"], consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = models.customers.get_item(uuid=data_dict["customer_uuid"], consistent=True)

    # Auto assign a delegator if one does not exists
    delegator_uuid = data_dict["delegator_uuid"] \
        if data_dict.get("delegator_uuid") is not None else find_delegator()

    transaction = Transaction(
            customer_uuid=data_dict["customer_uuid"],
            status=TransactionStatus.STARTED if not "status" in data_dict else data_dict["status"],
            delegator_uuid=delegator_uuid)

    # Add the transaction to the transaction table
    models.transactions.put_item(data=transaction.get_data())

    # Add the transaction uuid to the customer
    if customer["transaction_uuids"] is None:
        customer["transaction_uuids"] = []

    customer["transaction_uuids"].append(transaction.uuid)
    customer.save()

    return jsonpickle.encode({"result": 0, "uuid": transaction.uuid}, unpicklable=False)

@app.route('/transaction/<uuid>', methods=['GET', 'PUT'])
def transaction(uuid):
    if not models.transactions.has_item(uuid=uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    if request.method == 'PUT':
        data_dict = jsonpickle.decode(request.data.decode("utf-8"))

        transaction = models.transactions.get_item(uuid=uuid)

        for key in data_dict:
            transaction[key] = data_dict[key]

        transaction.save()

        return jsonpickle.encode({"result": 0}, unpicklable=False)
    elif request.method == 'GET':
        transaction = models.transactions.get_item(uuid=uuid, consistent=True)

        to_return = {"result": 0, "transaction": transaction._data}
        return jsonpickle.encode(to_return, unpicklable=False)

@app.route("/get_transactions_with_status/<status>", methods=['GET'])
def get_transactions_with_status(status):
    # NOTE: does not need to be consistent, b/c it will be called frequently
    query_result = models.transactions.query_2(index="status-index", status__eq=status)
    return jsonpickle.encode({
        "result": 0,
        "transactions": [transaction._data for transaction in query_result]},
        unpicklable=False)

@app.route('/sms_callback', methods=['POST'])
def sms_callback():
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    from_phone_number = data_dict["from"]["endpoint"]
    message_content = data_dict["message"]

    customer = None
    if models.customers.query_count(index="phone_number-index", phone_number__eq=from_phone_number) == 0:
        cur_customer = Customer(phone_number=from_phone_number)
        customer = models.customers.get_item(uuid=cur_customer["uuid"], consistent=True)

    for cur_customer in models.customers.query_2(index="phone_number-index", phone_number__eq=from_phone_number):
        customer = cur_customer

    current_transaction = None

    if customer["transaction_uuids"] is not None:
        for transaction_uuid in customer["transaction_uuids"]:
            transaction = models.transactions.get_item(uuid=transaction_uuid, consistent=True)
            if transaction["status"] == TransactionStatus.HELPED:
                current_transaction = transaction

    if current_transaction is None:
        delegator_uuid = find_delegator()
        delegator = models.delegators.get_item(uuid=delegator_uuid, consistent=True)

        temp_t = Transaction(
            customer_uuid=customer["uuid"],
            delegator_uuid=find_delegator())

        if customer["transaction_uuids"] is None:
            customer["transaction_uuids"] = []
        if delegator["transaction_uuids"] is None:
            delegator["transaction_uuids"] = []

        customer["transaction_uuids"].append(temp_t["uuid"])
        delegator["transaction_uuids"].append(temp_t["uuid"])

        delegator.save()

        models.transactions.put_item(data=temp_t.get_data())
        current_transaction = models.transactions.get_item(uuid=temp_t.uuid)

    message = Message(content=message_content, from_customer=True, platform_type="SMS")

    if current_transaction["messages"] is None:
        current_transaction["messages"] = []
    current_transaction["messages"].append(message.get_data())

    customer.save()
    current_transaction.save()

    return jsonpickle.encode({"result": 0})

####################
# Helper functions #
####################

def verify_dict_contains_keys(dic, keys):
    for cur_key in keys:
        if cur_key not in dic:
            return False

    return True

def find_delegator():
    all_delegators = models.delegators.scan()

    min_outstanding_trans = sys.maxint
    delegator_uuid = None
    for delegator in all_delegators:
        cur_count = 0

        if delegator["transaction_uuids"]:
            for transaction_uuid in delegator["transaction_uuids"]:
                transaction = models.transactions.get_item(uuid=transaction_uuid)
                if transaction["status"] == TransactionStatus.HELPED:
                    cur_count += 1

        if cur_count < min_outstanding_trans:
            min_outstanding_trans = cur_count
            delegator_uuid = delegator["uuid"]

    return delegator_uuid


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Starts the api server")
    parser.add_argument("--port", "-bp", dest="port", type=int, default=80, help="The port to bind to")
    parser.add_argument("--host", "-bh", dest="host", default="0.0.0.0", help="The hostname to bind to")

    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=True, threaded=True)
