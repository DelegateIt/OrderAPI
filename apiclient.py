#!/usr/bin/env python3.4

from requests import Request, Session
import logging
import json
import os

import sys

default_host = "localhost:8000"


def init_connection():
    from boto.dynamodb2.layer1 import DynamoDBConnection
    logging.getLogger("boto").setLevel(logging.INFO)
    host = "localhost"
    port = 8040

    #if inside a docker container linked to the db container
    if "DB_PORT" in os.environ:
        host = os.environ["DB_PORT"][6:].split(":")[0]
        port = os.environ["DB_PORT"][6:].split(":")[1]

    return DynamoDBConnection(
        aws_access_key_id='foo',
        aws_secret_access_key='bar',
        host=host,
        port=port,
        is_secure=False)

def clear_database(conn=None):
    from boto.dynamodb2.table import Table
    logging.getLogger("boto").setLevel(logging.INFO)

    if conn is None:
        conn = init_connection()

    tables = conn.list_tables()["TableNames"]
    for name in tables:
        tbl = Table(name, connection=conn)
        for item in tbl.scan():
            item.delete()

def send_api_request(method, components, json_data=None):
    components = [str(v) for v in components]
    url = "http://" + default_host + "/" + "/".join(components)
    if json_data is not None:
        json_data = json.dumps(json_data)

    s = Session()
    req = Request(method=method, url=url, data=json_data)
    prepped = s.prepare_request(req)

    resp = s.send(prepped)

    if resp.status_code != 200:
        print("bad response", resp.content.decode("utf-8"))
        raise Exception("Received bad status code {}".format(resp.status_code))

    json_data = resp.json()
    if json_data["result"] != 0:
        print("Received bad status code {} with response {}".format(json_data["result"], json_data))
    return resp.json()

def populate_with_dummy_data():
        dlgt = create_delegator("Test", "Delegator", "phone#1", "sfksdfj@ldjfd.com")
        print("Delegator", dlgt)
        c1 = create_customer("George", "Bush", "phone#2")
        c2 = create_customer("John", "Adams", "phone#3")
        c3 = create_customer("Andrew", "Johnson", "phone#4")
        c4 = create_customer("Creepy", "Nixon", "phone#5")
        c5 = create_customer("Frank", "Roosevelt", "phone#6")
        c6 = create_customer("Barack", "Obama", "phone#7")
        customers = [c1, c2, c3, c4, c5, c6]
        transactions = []
        for c in customers:
            transactions.append(create_transaction(c["uuid"]))
        print("Transactions", transactions)
        for t in transactions:
            update_transaction(t["uuid"], "helped", dlgt["uuid"])
        send_message(transactions[0]["uuid"], "test", "I want Pizza", True)
        send_message(transactions[1]["uuid"], "test", "How's it going?", True)
        send_message(transactions[2]["uuid"], "test", "Bring me the declaration of independence", True)
        send_message(transactions[3]["uuid"], "test", "lskjfklsdfjksjf", True)
        send_message(transactions[4]["uuid"], "test", "I need my lawn mowed pronto", True)
        send_message(transactions[5]["uuid"], "test", "you.. uh.. got anymore of the dank bud", True)

#######BEGIN api wrapper

def create_customer(first_name, last_name, phone_number):
    json_data = {
        "first_name": first_name,
        "last_name": last_name,
        "phone_number": phone_number
    }

    return send_api_request("POST", ["core", "customer"], json_data)

def get_customer(uuid):
    return send_api_request("GET", ["core", "customer", uuid])

def update_customer(uuid, update):
    return send_api_request("PUT", ["core", "customer", uuid], update)

def create_transaction(customer_uuid, delegator_uuid=None, status=None):
    json_data = {"customer_uuid": customer_uuid}
    if delegator_uuid is not None:
        json_data["delegator_uuid"] = delegator_uuid
    if status is not None:
        json_data["status"] = status

    return send_api_request("POST", ["core", "transaction"], json_data)

def get_transaction(transaction_uuid):
    return send_api_request("GET", ["core", "transaction", transaction_uuid])

def update_transaction(transaction_uuid, status=None, delegator_uuid=None):
    json_data = {}
    if status is not None:
        json_data["status"] = status
    if delegator_uuid is not None:
        json_data["delegator_uuid"] = delegator_uuid

    return send_api_request("PUT", ["core", "transaction", transaction_uuid], json_data)

def create_delegator(first_name, last_name, phone_number, email):
    json_data = {
        "phone_number": phone_number,
        "email": email,
        "first_name": first_name,
        "last_name": last_name
    }

    return send_api_request("POST", ["core", "delegator"], json_data)

def get_delegator(delegator_uuid):
    return send_api_request("GET", ["core", "delegator", delegator_uuid])

def get_delegator_list():
    return send_api_request("GET", ["core", "delegator"])

def update_delegator(delegator_uuid, update):
    return send_api_request("PUT", ["core", "delegator", delegator_uuid], update)

def send_message(transaction_uuid, platform_type, content, from_customer):
    if type(from_customer) is str:
        from_customer = from_customer.lower() == "true"
    json_data = {
        "platform_type": platform_type,
        "content": content,
        "from_customer": from_customer
    }

    return send_api_request("POST", ["core", "send_message", transaction_uuid], json_data)

def get_messages(transaction_uuid):
    return send_api_request("GET", ["core", "get_messages", transaction_uuid])

def transaction_change(transaction_uuid):
    return send_api_request("GET", ["streams", "transaction_change", transaction_uuid])

def generate_payment_form(transaction_uuid):
    return send_api_request("GET", ["core", "payment", "uiform", transaction_uuid])

######END api wrapper

if __name__ == "__main__":
    method_map = {
        "get_messages": get_messages,
        "send_message": send_message,
        "get_delegator": get_delegator,
        "create_delegator": create_delegator,
        "update_transaction": update_transaction,
        "get_transaction": get_transaction,
        "create_transaction": create_transaction,
        "get_customer": get_customer,
        "create_customer": create_customer,
        "generate_payment_form": generate_payment_form,
        "get_delegator_list": get_delegator_list,
        #End api wrapper methods
        "clear_database": clear_database,
        "populate": populate_with_dummy_data,
    }

    method = "--help"
    args = []
    if len(sys.argv) > 1:
        method = sys.argv[1]
        args = sys.argv[2:]

    needs_help = method == "--help" or method == "-h"
    if not needs_help and method not in method_map:
        print("Error: {} not in the list of available methods".format(method))
        needs_help = True

    if needs_help:
        print("DelegateIt API python wrapper.")
        print("Usage:")
        print("\tscript.py method_name [method_arg_1] [method_arg_2] ...")
        print("Examples:")
        print("\tscript.py create_customer jon doe 1113334444")
        print("\tscript.py send_message 3934020959504 sms 'hows it going?'")
        print("Available methods:")
        for k in method_map.keys():
            print("\t{}".format(k))
        exit(1)

    print(method_map[method](*args))
