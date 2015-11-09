#!/usr/bin/env python3
""" The misc and utility file

Put things in here that are scripts or tangential
uses of the backend
"""

from gator.service import sms
import copy
import gator.models
import sys

def mass_text(body_fn, numbers_fn):
    body = open(body_fn, "r").read()

    with open(numbers_fn, "r") as cur_file:
        cur_line = cur_file.readline()
        while cur_line != "":
            sms.send_msg(cur_line, body)
            cur_line = cur_file.readline()

def retreive_transaction_info():
    customers = {}
    for t in gator.models.transactions.scan():
        if t["customer_uuid"] not in customers:
            customers[t["customer_uuid"]] = {
                "transactions": []
            }
        transaction = copy.deepcopy(t._data)
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


if __name__ == "__main__":
    method_map = {
        "mass_text": mass_text
    }

    method = None
    args = []
    if len(sys.argv) > 1:
        method = sys.argv[1]
        args = sys.argv[2:]

    if method is None:
        print("Please specify a method to execute.")
        exit(0)

    method_map[method](*args)
