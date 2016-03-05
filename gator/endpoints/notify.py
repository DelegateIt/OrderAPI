import json
import jsonpickle
import requests

from flask import request

import gator.core.common as common
import gator.core.models as models

from gator.flask import app
from gator.core.auth import authenticate, validate_permission, Permission, validate_token
from gator.core.models import Model, TFields, Transaction

def add_handler(ip_address, port, expires):
    data = {
        "ip_address": ip_address,
        "port": port,
        "expires": expires
    }
    models.handlers.put_item(data=data, overwrite=True)
    return data

def get_handlers():
    query = models.handlers.scan()
    return [h._data for h in query]

def purge_handlers():
    query = models.handlers.scan()
    time = common.get_current_timestamp() // 10**6
    for handler in query:
        if handler["expires"] < time:
            handler.delete()

def notify_handlers(transaction_uuid):
    transaction = Model.load_from_db(Transaction, transaction_uuid)
    payload = jsonpickle.encode({"result": 0, "transaction": transaction.get_data()})
    handlers = models.handlers.scan()
    headers = {"Content-Type": "application/json"}

    for handler in handlers:
        url = "http://%s:%s/transaction_change" % (handler["ip_address"], handler["port"])
        try:
            requests.post(url, data=payload, headers=headers, timeout=0.5)
        except requests.exceptions.RequestException:
            pass #Ignore the exception. The handler is stale

@app.route("/notify/handler", methods=["POST"])
def flask_add_handler():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.API_NOTIFY])

    expires = (common.get_current_timestamp() // 10**6) + 60 * 60 * 12 #time + 12 hours
    ip_address = request.remote_addr
    if "x-forwarded-for" in request.headers:
        ip_address = request.headers.get("x-forwarded-for").split(",")[0]

    port = jsonpickle.decode(request.data.decode("utf-8"))["port"]
    handler = add_handler(ip_address, port, expires)
    return jsonpickle.encode({"result": 0, "handler": handler})

@app.route("/notify/handler", methods=["GET"])
def flask_get_handler():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.API_NOTIFY])

    handlers = get_handlers()
    return jsonpickle.encode({"result": 0, "handlers": handlers})

@app.route("/notify/handler", methods=["DELETE"])
def flask_purge_handlers():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.API_NOTIFY])

    purge_handlers()
    return jsonpickle.encode({"result": 0})

@app.route("/notify/broadcast/<transaction_uuid>", methods=["POST"])
def flask_broadcast(transaction_uuid):
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.API_NOTIFY])

    notify_handlers(transaction_uuid)
    return jsonpickle.encode({"result": 0})
