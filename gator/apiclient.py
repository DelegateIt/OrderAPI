#!/usr/bin/env python3

from requests import Request, Session
import urllib.parse
import json
import os
import argparse

import sys

default_host = "localhost:8000"
auth_token = "MjAzOTQ4NTA0OTU5MzA6YXBpOjE2MDQ3MzA0MjU6bVNLZ2hLOXFkUjAzdnIzbjlPanpwU1BpZWV1MldrME1DWlNIMmdGK2orST0="

def init_connection():
    from boto.dynamodb2.layer1 import DynamoDBConnection
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

    if conn is None:
        conn = init_connection()

    tables = conn.list_tables()["TableNames"]
    for name in tables:
        tbl = Table(name, connection=conn)
        for item in tbl.scan():
            item.delete()

def send_api_request(method, components, json_data=None, token=None, query=None):
    components = [str(v) for v in components]
    url = "http://" + default_host + "/" + "/".join(components)
    query = query if query is not None else {}
    if token is not None:
        query.update({"token": token})
    if query != {}:
        url += "?" + urllib.parse.urlencode(query)
    if json_data is not None:
        json_data = json.dumps(json_data)

    s = Session()
    req = Request(method=method, url=url, data=json_data)
    prepped = s.prepare_request(req)

    resp = s.send(prepped)

    if resp.status_code != 200 and resp.status_code != 400:
        print("bad response", resp.content.decode("utf-8"))
        raise Exception("Received bad status code {}".format(resp.status_code))

    json_data = resp.json()
    if json_data["result"] != 0:
        print("Received bad status code {} with response {}".format(json_data["result"], json_data))
    return resp.json()

def populate_with_dummy_data():
        dlgt = create_delegator("Test", "Delegator", "phone#1", "sfksdfj@ldjfd.com", "1", "1")
        print("Delegator", dlgt)
        c1 = create_customer("George", "Bush", "phone#2", "2", "")
        c2 = create_customer("John", "Adams", "phone#3", "3", "")
        c3 = create_customer("Andrew", "Johnson", "phone#4", "4", "")
        c4 = create_customer("Creepy", "Nixon", "phone#5", "5", "")
        c5 = create_customer("Frank", "Roosevelt", "phone#6", "6", "")
        c6 = create_customer("Barack", "Obama", "phone#7", "7", "")
        customers = [c1, c2, c3, c4, c5, c6]
        transactions = []
        for c in customers:
            transactions.append(create_transaction(c["uuid"], "sms"))
        print("Transactions", transactions)
        for t in transactions:
            update_transaction(t["uuid"], "helped", dlgt["uuid"])
        send_message(transactions[0]["uuid"], "I want Pizza", True)
        send_message(transactions[1]["uuid"], "How's it going?", True)
        send_message(transactions[2]["uuid"], "Bring me the declaration of independence", True)
        send_message(transactions[3]["uuid"], "lskjfklsdfjksjf", True)
        send_message(transactions[4]["uuid"], "I need my lawn mowed pronto", True)
        send_message(transactions[5]["uuid"], "you.. uh.. got anymore of the dank bud", True)

#######BEGIN api wrapper

def create_customer(first_name, last_name, phone_number=None, fbuser_id=None, fbuser_token=None):
    json_data = {
        "first_name": first_name,
        "last_name": last_name,
    }
    if phone_number is not None:
        json_data["phone_number"] = phone_number
    if fbuser_id is not None:
        json_data["fbuser_id"] = fbuser_id
    if fbuser_token is not None:
        json_data["fbuser_token"] = fbuser_token

    return send_api_request("POST", ["core", "customer"], json_data, token=auth_token)

def get_customer(uuid):
    return send_api_request("GET", ["core", "customer", uuid], token=auth_token)

def update_customer(uuid, update):
    return send_api_request("PUT", ["core", "customer", uuid], update, token=auth_token)

def create_transaction(customer_uuid, customer_platform_type):
    json_data = {"customer_uuid": customer_uuid, "customer_platform_type": customer_platform_type}
    return send_api_request("POST", ["core", "transaction"], json_data, token=auth_token)

def get_transaction(transaction_uuid):
    return send_api_request("GET", ["core", "transaction", transaction_uuid], token=auth_token)

def update_transaction(transaction_uuid, status=None, delegator_uuid=None, receipt=None):
    json_data = {}
    if status is not None:
        json_data["status"] = status
    if delegator_uuid is not None:
        json_data["delegator_uuid"] = delegator_uuid
    if receipt is not None:
        json_data["receipt"] = receipt

    return send_api_request("PUT", ["core", "transaction", transaction_uuid], json_data, token=auth_token)

def create_delegator(first_name, last_name, phone_number, email, fbuser_id=None, fbuser_token=None):
    json_data = {
        "phone_number": phone_number,
        "email": email,
        "first_name": first_name,
        "last_name": last_name
    }
    if fbuser_id is not None:
        json_data["fbuser_id"] = fbuser_id
    if fbuser_token is not None:
        json_data["fbuser_token"] = fbuser_token

    return send_api_request("POST", ["core", "delegator"], json_data, token=auth_token)

def get_delegator(delegator_uuid):
    return send_api_request("GET", ["core", "delegator", delegator_uuid], token=auth_token)

def get_delegator_list():
    return send_api_request("GET", ["core", "delegator"], token=auth_token)

def update_delegator(delegator_uuid, update):
    return send_api_request("PUT", ["core", "delegator", delegator_uuid], update, token=auth_token)

def send_message(transaction_uuid, content, from_customer, mtype="text"):
    if type(from_customer) is str:
        from_customer = from_customer.lower() == "true"
    json_data = {
        "content": content,
        "from_customer": from_customer,
        "type": mtype
    }

    return send_api_request("POST", ["core", "send_message", transaction_uuid], json_data, token=auth_token)

def get_messages(transaction_uuid):
    return send_api_request("GET", ["core", "get_messages", transaction_uuid], token=auth_token)

def transaction_change(transaction_uuid):
    return send_api_request("GET", ["streams", "transaction_change", transaction_uuid], token=auth_token)

def generate_payment_form(transaction_uuid):
    return send_api_request("GET", ["core", "payment", "uiform", transaction_uuid], token=auth_token)

def assign_new_transaction(delegator_uuid):
    return send_api_request("GET", ["core", "assign_transaction", delegator_uuid], token=auth_token)

def fb_login_customer(fbuser_id, fbuser_token):
    data = {
        "fbuser_id": fbuser_id,
        "fbuser_token": fbuser_token
    }
    return send_api_request("POST", ["core", "login", "customer"], data)

def fb_login_delegator(fbuser_id, fbuser_token):
    data = {
        "fbuser_id": fbuser_id,
        "fbuser_token": fbuser_token
    }
    return send_api_request("POST", ["core", "login", "delegator"], data)

def add_notify_handler(port):
    data = {"port": port}
    return send_api_request("POST", ["notify", "handler"], data, token=auth_token)

def get_notify_handlers():
    return send_api_request("GET", ["notify", "handler"], token=auth_token)

def purge_notify_handlers():
    return send_api_request("DELETE", ["notify", "handler"], token=auth_token)

def broadcast_transaction(transaction_uuid):
    return send_api_request("POST", ["notify", "broadcast", transaction_uuid], token=auth_token)

def send_sms_to_api(from_phone_num, message):
    query = {
        "From": from_phone_num,
        "Body": message
    }
    return send_api_request("POST", ["sms", "handle_sms"], token=auth_token, query=query)

def get_payment_cards(customer_uuid):
    return send_api_request("GET", ["payment", "card", customer_uuid], token=auth_token)

def add_payment_card(customer_uuid, stripe_token):
    data = {"stripe_token": stripe_token}
    return send_api_request("POST", ["payment", "card", customer_uuid], data, token=auth_token)

def delete_payment_card(customer_uuid, card_id):
    data = {"stripe_card_id": card_id}
    return send_api_request("DELETE", ["payment", "card", customer_uuid], data, token=auth_token)

def charge_transaction_payment(transaction_uuid, stripe_source, email=None):
    data = {"stripe_source": stripe_source}
    if email is not None:
        data["email"] = email
    return send_api_request("POST", ["payment", "charge", transaction_uuid], data, token=auth_token)


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

    parser = argparse.ArgumentParser(description="DelegateIt low-level api client")
    parser.add_argument("method", choices=method_map.keys(), help="The method to call")
    parser.add_argument('args', nargs=argparse.REMAINDER,
            help="Any arguments to pass to the method")


    args = parser.parse_args()

    print(method_map[args.method](*args.args))
