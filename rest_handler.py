from flask import Flask, request

import time
import json

import models
import common

from models import Customer, Message
from common import Errors

app = Flask(__name__)

session = models.Session()

VALID_PLATFORMS = ["sms"]

@app.route('/')
def index():
    return "GatorRestService is up and running!"

@app.route('/send_message/<phone_number>', methods=['POST'])
def send_message(phone_number):
    data_dict = json.loads(request.data)
    if not verify_dict_contains_keys(data_dict, ["content", "platform_type"]):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    elif data_dict["platform_type"] not in VALID_PLATFORMS:
        return common.error_to_json(Errors.UNSUPPORTED_PLATFORM)

    customer_query_result = session.query(Customer). \
    session.query(Customer). \
        filter_by(phone_number=phone_number)

    if customer_query_result.count() == 0:
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    cur_time = int(round(time.time() * 1000))
    message = Message(content=data_dict["content"], timestamp=cur_time)

    customer = customer_query_result[0]
    customer.messages.append(message)

    session.commit()

    return json.dumps({
            "result": 0,
    	    "timestamp": cur_time
        })

@app.route('/get_messages/<phone_number>', methods=['GET'])
def get_messages(phone_number):
    customer_messages_query_result = db.session.query(Custoemr.messages). \
        filter_by(phone_number=phone_number)

    if len(customer_query_result) == 0:
        return common.error_to_json(Errors.USER_DOES_NOT_EXIST)

    return json.dumps(customer_messages_query_result)

@app.route('/get_messages_past_time/<phone_number>/<timestamp>')
def get_messages_past_time(phone_number, timestamp):
    timestamp = int(timestamp)
    if phone_number not in message_store:
        return json.dumps(None)
    else:
        messages_past = [message for message in message_store[phone_number] if message["timestamp"] > timestamp]
	if len(messages_past) == 0:
	    return json.dumps(None)
	else:
	    return json.dumps(messages_past)

@app.route('/mark_transaction_started/<phone_number>')
def mark_transaction_started(phone_number):
    if phone_number in message_store:
        user_data = message_store[phone_number]
    else:
        return json.dumps({"success": False})

    with transaction_lock:
        user_data["transaction_status"] = TRANSACTION_STARTED

    return json.dumps({"success": True})

@app.route('/mark_transaction_helped/<phone_number>')
def mark_transaction_helped(phone_number):
    if phone_number in message_store:
        user_data = message_store[phone_number]
    else:
        return json.dumps({"success": False})

    with transaction_lock:
        user_data["transaction_status"] = TRANSACTION_HELPED

    return json.dumps({"success": True})

@app.route('/mark_transaction_completed/<phone_number>')
def mark_transaction_complete(phone_number):
    if phone_number in message_store:
        user_data = message_store[phone_number]
    else:
        return json.dumps({"success": False})

    with transaction_lock:
        user_data["transaction_status"] = TRANSACTION_COMPLETE

    return json.dumps({"success": True})

@app.route('/get_unhelped_transactions/')
def get_unhelped_transactions():
    return [user_data for user_data in message_store \
            if "transaction_status" in user_data \
            and user_data["transaction_status"] == TRANSACTION_STARTED]

@app.route('/customer/<phone_number>', methods=['POST', 'GET'])
def customer(phone_number):
    customer_query_result = session.query(Customer). \
                            filter_by(phone_number=phone_number)

    if request.method == 'POST':
        if customer_query_result.count() != 0:
            return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

        data_dict = json.loads(request.data)

        if not verify_dict_contains_keys(data_dict, ["first_name", "last_name"]):
            return common.error_to_json(Errors.DATA_NOT_PRESENT)

        customer = Customer(first_name=data_dict["first_name"],
                            last_name=data_dict["last_name"],
                            phone_number=phone_number)

        session.add(customer)
        session.commit()

        return json.dumps({"result": 0})
    elif request.method == 'GET':
        if customer_query_result.count() == 0:
            return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

        return customer_query_result[0].to_json()

# Helper functions
def verify_dict_contains_keys(dic, keys):
    for cur_key in dic:
        if cur_key not in keys:
            return False

    return True

if __name__ == '__main__':
    models.init()
    app.run(host="0.0.0.0", port=8080, debug=True)
