from flask import request
from flask.ext.socketio import SocketIO, send, join_room, leave_room

import jsonpickle

import gator.common
from gator import app, socketio

###############
# Global Vars #
###############

MY_IP = gator.common.get_public_ip()

@app.route("/streams/get_server_ip", methods=["GET"])
def get_server_ip():
    return jsonpickle.encode({"result": 0, "ip": MY_IP});

@app.route("/streams/transaction_change/<transaction_uuid>", methods=["GET"])
def transaction_change(transaction_uuid):
    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return gator.common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)

    # Send the data back to the client
    socketio.send(jsonpickle.encode(transaction._data), room=transaction_uuid)

    return jsonpickle.encode({"result": 0})

@socketio.on("register_transaction")
def on_register_transaction(data):
    transaction_uuid = data["transaction_uuid"]

    # Register a room for this transaction_uuid
    join_room(transaction_uuid)

    # Update global state
    if not gator.models.handlers.has_item(transaction_uuid=transaction_uuid, consistent=True):
        gator.models.handlers.put_item(data={
            "transaction_uuid": transaction_uuid,
            "handlers": [MY_IP]})
    else:
        cur_handlers = gator.models.handlers.get_item(transaction_uuid=transaction_uuid, consistent=True)
        if MY_IP not in cur_handlers:
            cur_handlers["handlers"].append(MY_IP)
            cur_handlers.partial_save()

@socketio.on("forget_transaction")
def on_forget_transaction(data):
    transaction_uuid = data["transaction_uuid"]

    # Leave the room for this transaction_uuid
    leave_room(transaction_uuid)

    # Clean up global state
    handlers = gator.models.handlers.get_item(transaction_uuid=transaction_uuid, consistent=True)

    if len(handlers["handlers"]) == 1:
        handlers.delete()
    else:
        handlers["handlers"].remove(MY_IP)
        handlers.partial_save()

