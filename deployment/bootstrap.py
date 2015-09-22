#!/usr/bin/env python2

import requests
import json

import boto.dynamodb2
from boto.dynamodb2.table import Table

import uuid
import os.path
import io

# Custom import for common
import sys
sys.path.insert(0, os.path.abspath("../gator"))

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
            json.dump({"ip": public_ip, "uuid": common.get_uuid()}, egg_file)

    # Open if exists, else create the egg
    with open(egg_path, "r+") as egg_file:
        egg_data = json.load(egg_file)

        # Scan the DB and check to see if any of the handlers were the prev instance
        # of the Rest API on this machine
        for item in handlers.scan():
   	    if egg_data["ip"] in item["handlers"]:
                item["handlers"] = filter(lambda a: a != egg_data["ip"], item["handlers"])
                if (len(item["handlers"]) == 0):
                    item.delete()
                else:
	            item.partial_save()

        # We have removed all stale data from the DB it is safe to overwrite it
        egg_data = {"ip": public_ip, "uuid": common.get_uuid()}
        egg_file.truncate(0)
        egg_file.seek(0)
        egg_file.write(json.dumps(egg_data))

if __name__ == "__main__":
    bootstrap()
