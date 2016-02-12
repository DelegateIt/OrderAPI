import threading
import queue
import logging
import json
from requests import Session, Request
from flask import Flask, request

logging.getLogger().setLevel(logging.INFO)

app = Flask(__name__)
session = Session()
allowed_methods = ["GET", "POST", "HEAD", "DELETE", "OPTIONS", "PATCH"]
event_queue = None

def _process_event(event):
    record = {
        "dynamodb": {
            "Keys": None
        }
    }
    if "Key" in event:
        record["dynamodb"]["Keys"] = event["Key"]
    elif "Item" in event:
        record["dynamodb"]["Keys"] = {}
        record["dynamodb"]["Keys"]["uuid"] = event["Item"]["uuid"]
    else:
        raise Exception("Unable to process event " + repr(event))
    return record

def _send_records(update_url, events):
    logging.info("Sending records to lambda: %s", events)
    headers={"Content-Type": "application/json"}
    session.post(update_url, data=json.dumps({"Records": events}), headers=headers)

def _batch_records(batch_size, update_url, event_queue):
    on_deck = []
    while True:
        send_update = False
        timeout = None if len(on_deck) == 0 else 1.0
        try:
            event = event_queue.get(timeout=timeout)
            record = _process_event(event)
            on_deck.append(record)
            send_update = len(on_deck) >= batch_size
        except queue.Empty:
            send_update = True
        if send_update:
            _send_records(update_url, on_deck)
            on_deck = []

def _intercept_dynamo(response, valid_tables):
    if response.status_code != 200 or response.request.method != "POST":
        return

    request_data = json.loads(response.request.body.decode("utf-8"))
    if "TableName" not in request_data or request_data["TableName"] not in valid_tables:
        return
    if "AttributeUpdates" in request_data or "Item" in request_data:
        logging.info("Change in db item detected: %s", request_data)
        event_queue.put(request_data)

@app.route('/', defaults={'path': ''}, methods=allowed_methods)
@app.route('/<path:path>', methods=allowed_methods)
def _catch_all(path):

    logging.debug("\t  * HEADERS: " + ", ".join([k + ": " + v for k,v in request.headers.items()]))
    logging.debug("\t  * DATA: " + request.data.decode("utf-8"))

    url = "http://localhost:8041" + request.path
    req = Request(method=request.method, url=url, data=request.data, headers=request.headers)
    prepped = session.prepare_request(req)
    resp = session.send(prepped)

    logging.debug("  * Intercepted response")
    logging.debug("\t  * STATUS: " + str(resp.status_code))
    logging.debug("\t  * HEADERS: " + ", ".join([k + ": " + v for k,v in resp.headers.items()]))
    logging.debug("\t  * DATA: " + resp.content.decode("utf-8"))

    try:
        _intercept_dynamo(resp, ["DelegateIt_Transactions_CD"])
    except Exception as e:
        logging.exception(e)

    return (resp.content, resp.status_code, resp.headers.items())

def _start_emulator_thread(batch_size, update_url):
    event_queue = queue.Queue()
    thread = threading.Thread(target=_batch_records, args=(batch_size, update_url, event_queue))
    thread.start()
    return event_queue

event_queue = _start_emulator_thread(batch_size=1, update_url="http://localhost:8061/process_records")
