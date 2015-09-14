#!/usr/bin/env python2

import requests
import json

import boto.dynamodb2
from boto.dynamodb2.table import Table

import uuid
import os.path
import io

# Fix issues with unverified requests
import urllib3
requests.packages.urllib3.disable_warnings()

# Custom import for common
import sys
sys.path.insert(0, os.path.abspath("../"))

import common

##############################
# Global vars, consts, extra #
##############################

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
        aws_secret_access_key="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")

# Tables
handlers = Table("DelegateIt_Handlers", connection=conn)

# Config Stuff
egg_path = "./egg.json"

def bootstrap():
    public_ip = common.get_public_ip()

    # Initialize the file if it doesn't exists
    if not os.path.isfile(egg_path):
        with open(egg_path, "w+") as egg_file:
            json.dump({"prev_insts": {}}, egg_file)

    # Open if exists, else create the egg
    with open(egg_path, "r+") as egg_file:
        egg_data = json.load(egg_file)

        # Checks to see if the handler is contained in the egg
        def handler_is_stale(handler):
            for old_handler in egg_data["prev_insts"]:
                print "old handler: %s" % old_handler
                if old_handler["uuid"] == handler["uuid"] and old_handler["ip"] == handler["ip"]:
                    return True
            return False

        # Scan the DB and check to see if any of the handlers were prev instances
        # of the Rest API on this machine
        for item in handlers.scan():
            print item._data
            new_handlers = filter(handler_is_stale, item["handlers"])

            if item["handlers"] != new_handlers:
                item.partial_save()

        # We have removed all stale data from the DB it is safe to overwrite it
        egg_data["prev_insts"] = {"ip": public_ip, "uuid": common.get_uuid()}
        egg_file.truncate(0)
        egg_file.seek(0)
        egg_file.write(json.dumps(egg_data))

if __name__ == "__main__":
    bootstrap()
