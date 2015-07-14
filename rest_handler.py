from flask import Flask

import models
from common import Exceptions

app = Flask(__name__)

@app.route('/')
def index():
    return "Hello, World!"

@app.route('/send_message/<phone_number>/<content>')
def send_message(phone_number, content):
    session = models.Session()

    customer_query_result = session.query(Customer)
    if len(customer_query_result) == 0:
        return json.dumps({"Error": Exceptions.USER_DOES_NOT_EXIST})

    cur_time = int(round(time.time() * 1000))

    message = models.Message(content=content)
    customer_query_result[0].messages.append(message)

    session.commit()

    return json.dumps({
            "phone_number": phone_number,
		    "message": content,
		    "timestamp": cur_time
        })

@app.route('/get_messages/<phone_number>')
def get_messages(phone_number):
    if phone_number not in message_store:
        return json.dumps(None)
    else:
        return json.dumps(message_store[phone_number])

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

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
