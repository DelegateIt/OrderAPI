from flask import Flask, request

import time
import jsonpickle

import models
import common

from models import Customer, Message, Delegator, Transaction
from common import Errors, TransactionStatus

app = Flask(__name__)
app.debug = True

@app.route('/')
def index():
    return "GatorRestService is up and running!"

@app.route('/customer/<phone_number>', methods=['POST', 'GET'])
def customer(phone_number):
    if request.method == 'POST':
        if models.customers.has_item(phone_number=phone_number, consistent=True):
            return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

        data_dict = jsonpickle.decode(request.data)

        if not verify_dict_contains_keys(data_dict, ["first_name", "last_name"]):
            return common.error_to_json(Errors.DATA_NOT_PRESENT)

        customer = Customer(first_name=data_dict["first_name"], last_name=data_dict["last_name"], phone_number=phone_number)
        models.customers.put_item(data=customer.get_data())

        return jsonpickle.encode({"result": 0}, unpicklable=False)
    elif request.method == 'GET':
        if not models.customers.has_item(phone_number=phone_number, consistent=True):
            return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

        customer = models.customers.get_item(phone_number=phone_number, consistent=True)

        to_return = {"result": 0}
        to_return.update(customer._data)
        return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/send_message/<phone_number>', methods=['POST'])
def send_message(phone_number):
    data_dict = jsonpickle.decode(request.data)

    if not verify_dict_contains_keys(data_dict, ["content", "platform_type"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    if not models.customers.has_item(phone_number=phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    message = Message(content=data_dict["content"], platform_type=data_dict["platform_type"])
    customer = models.customers.get_item(phone_number=phone_number, consistent=True)

    if customer["messages"] is None:
        customer["messages"] = []

    customer["messages"].append(message.get_data())

    # Save data to the database
    customer.save()

    return jsonpickle.encode({
            "result": 0,
            "timestamp": message.timestamp
        }, unpicklable=False)

@app.route('/get_messages/<phone_number>', methods=['GET'])
def get_messages(phone_number):
    if not models.customers.has_item(phone_number=phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = models.customers.get_item(phone_number=phone_number, consistent=True)

    return jsonpickle.encode({"result": 0, "messages": customer["messages"]}, unpicklable=False)

@app.route('/get_messages_past_timestamp/<phone_number>/<timestamp>', methods=['GET'])
def get_messages_past_timestamp(phone_number, timestamp):
    if not models.customers.has_item(phone_number=phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    messages = models.customers.get_item(phone_number=phone_number, consistent=True)["messages"]
    timestamp = int(timestamp)

    return jsonpickle.encode({
        "result": 0,
        "messages": [message for message in messages if int(message["timestamp"]) > timestamp]},
        unpicklable=False)

@app.route('/transaction/<customer_phone_number>', methods=['GET', 'POST', 'PUT'])
def transaction(customer_phone_number):
    if not models.customers.has_item(phone_number=customer_phone_number, consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    if request.method == 'POST':
        data_dict = jsonpickle.decode(request.data)

        transaction = Transaction(
                customer_phone_number = customer_phone_number,
                status = TransactionStatus.STARTED if not data_dict.has_key("status") else data_dict["status"],
                delegator_phone_number =  data_dict["delegator_phone_number"] if data_dict.has_key("delegator_phone_number") else None)

        models.transactions.put_item(data=transaction.get_data())

        return jsonpickle.encode({"result": 0}, unpicklable=False)
    elif request.method == 'PUT':
        data_dict = jsonpickle.decode(request.data)

        if not models.transactions.has_item(customer_phone_number=customer_phone_number, consistent=True):
            return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

        transaction = models.transactions.get_item(customer_phone_number=customer_phone_number)

        for key in data_dict:
            transaction[key] = data_dict[key]

        transaction.save()

        return jsonpickle.encode({"result": 0}, unpicklable=False)
    elif request.method == 'GET':
        transaction = models.transactions.get_item(customer_phone_number=customer_phone_number, consistent=True)

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

@app.route("/sms_callback", methods=["POST"])
def sms_callback():
    print jsonpicke.decode(request.data)

####################
# Helper functions #
####################

def verify_dict_contains_keys(dic, keys):
    for cur_key in dic:
        if cur_key not in keys:
            return False

    return True

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
