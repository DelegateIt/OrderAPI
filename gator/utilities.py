#!/usr/bin/env python3

""" The misc and utility file

Put things in here that are scripts or tangential
uses of the backend
"""

import argparse
import copy
import sys
import os
import base64

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "../../../"))

import gator.core.models as models

from gator.core.models import Customer, Delegator, Transaction

def mass_text(body_fn, numbers_fn):
    from gator.core.service import sms
    body = open(body_fn, "r").read()

    with open(numbers_fn, "r") as cur_file:
        cur_line = cur_file.readline()
        while cur_line != "":
            sms.send_msg(cur_line, body)
            cur_line = cur_file.readline()

def retreive_transaction_info():
    import gator.core.models as models
    import gator.core.common as common
    from gator.core.models import Transaction, TFields
    customers = {}
    for t in common.convert_query(Transaction, models.transactions.scan()):
        if t["customer_uuid"] not in customers:
            customers[t["customer_uuid"]] = {
                "transactions": []
            }
        transaction = copy.deepcopy(t.get_data())
        del transaction["customer_uuid"]
        del transaction["payment_url"]
        if "messages" in transaction:
            del transaction["messages"]
        customers[t["customer_uuid"]]["transactions"].append(transaction)
    customer_info = {}
    for uuid, c in customers.items():
        customer_info[uuid] = {}
        customer_info[uuid]["transaction_count"] = len(c["transactions"])
        paid = [t for t in c["transactions"] if "receipt" in t and "stripe_charge_id" in t["receipt"]]
        customer_info[uuid]["transactions_paid"] = len(paid)
        customer_info[uuid]["revenue"] = sum([int(t["receipt"]["total"]) for t in paid])
    global_info = {}
    global_info["total_customers"] = len(customer_info)
    global_info["total_revenue"] = sum([c["revenue"] for c in customer_info.values()])
    global_info["total_transactions"] = sum([c["transaction_count"] for c in customer_info.values()])
    global_info["total_paid_transactions"] = sum([c["transactions_paid"] for c in customer_info.values()])
    global_info["customers_1_transaction"] = len([c for c in customer_info.values() if c["transaction_count"] == 1])
    global_info["customers_2_transaction"] = len([c for c in customer_info.values() if c["transaction_count"] == 2])
    global_info["customers_3_transaction"] = len([c for c in customer_info.values() if c["transaction_count"] == 3])
    global_info["customers_4_transaction"] = len([c for c in customer_info.values() if c["transaction_count"] == 4])
    return (global_info, customer_info, customers)

def generate_entropy(size=128):
    return base64.b64encode(os.urandom(size)).decode("utf-8")

def generate_api_key(key_type):
    import gator.core.auth as auth
    from gator.core.common import get_uuid
    permission_map = {
        "admin": ["API_SMS", "API_NOTIFY", "DELEGATOR_OWNER", "CUSTOMER_OWNER", "ALL_DELEGATORS", "ADMIN"],
        "sms": ["API_SMS"],
        "notify": ["API_NOTIFY"]
    }
    permission = permission_map[key_type]
    uuid = get_uuid()
    expires = 5 * 356 * 24 * 60 * 60 # 5 years.. chosen by fair dice roll
    token = auth.generate_token(uuid, auth.UuidType.API, expires)
    return {
        "token": token,
        "permissions": permission,
        "id": uuid
    }

def migrate_db(tablename):
    colloquial_table_names = {
        "customers":    Customer,
        "delegators":   Delegator,
        "transactions": Transaction
    }

    num_failures = 0
    total_migrations = 0
    tragic_failure = False
    model_cls = colloquial_table_names[tablename]

    for item in model_cls.TABLE.scan():
        # Necessary for first migration
        if item.get("version") is None:
            item["version"] = 0

        version = int(item["version"])
        if version < model_cls.VERSION:
            model_cls.HANDLERS.migrate_forward_item(item)
            num_failures += not item.save()
            total_migrations += 1
        elif version > model_cls.VERSION:
            # This only happens if you screwed up
            tragic_failure = True
            num_failures += 1

    if tragic_failure:
        print ("WARNING TRAGIC FAILURE: item versions are inconsistent\n")

    print ("Migration was %s\nTotal Failures: %s\nTotal Migrations: %s" % (
        "SUCCESSFUL" if num_failures == 0 else "UNSUCCESSFUL",
        num_failures, total_migrations))

if __name__ == "__main__":
    actions = {
        "mass_text": mass_text,
        "retreive_transaction_info": retreive_transaction_info,
        "generate_entropy": generate_entropy,
        "generate_api_key": generate_api_key,
        "migrate_db": migrate_db
    }

    choices = actions.keys()

    parser = argparse.ArgumentParser(
        description="Command line wrapper for miscellaneous utility functions",
        epilog="Valid commands: [%s]" % ", ".join(choices))

    parser.add_argument("command", type=str, choices=choices, help="Action to execute")
    parser.add_argument("args", nargs="*", help="Args to pass to action")

    args = parser.parse_args()
    actions[args.command](*args.args)
