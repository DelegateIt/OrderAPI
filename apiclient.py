#!/usr/bin/env python3

from requests import Request, Session
import json

import sys

import boto.dynamodb2
from boto.dynamodb2.table import Table

default_host = "localhost:8000"

def clear_database(conn=None):
    if conn is None:
        conn = boto.dynamodb2.connect_to_region(
                "us-west-2",
                aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
                aws_secret_access_key="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")

    customers    = Table("DelegateIt_Customers", connection=conn)
    delegators   = Table("DelegateIt_Delegators", connection=conn)
    transactions = Table("DelegateIt_Transactions", connection=conn)

    for table in [customers, delegators, transactions]:
        for item in table.scan():
            item.delete()

def send_api_request(method, components, json_data=None):
    components = [str(v) for v in components]
    url = "http://" + default_host + "/" + "/".join(components)

    s = Session()
    req = Request(method=method, url=url, json=json_data)
    prepped = s.prepare_request(req)

    resp = s.send(prepped)

    if resp.status_code != 200:
        print("bad response", resp.content.decode("utf-8"))
        raise Exception("Received bad status code {}".format(resp.status_code))

    json_data = resp.json()
    if json_data["result"] != 0:
        print("Received bad status code {} with response {}".format(json_data["result"], json_data))
    return resp.json()

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
