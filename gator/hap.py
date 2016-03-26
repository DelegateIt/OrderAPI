#!/usr/bin/env python3

import re
import os
import sys
import time
import json
import requests
import argparse
import logging

logging.getLogger().setLevel(logging.INFO)

session = requests.Session()

# Converts a pages search results to a list of propertyIds
# [t["propertyId"] for t in s["results"]["hits"] if t["propertyId"].find("vb") == -1]

def request_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36"
    }
    req = requests.Request(method="GET", url=url, headers=headers)
    return session.send(session.prepare_request(req), timeout=4).text


def search_ha_properties(page=1):
    """ searches the ha properties """
    url = ("https://www.homeaway.com/ajax/map/search/texas/austin/region:7116/" +
          "keywords:Austin%2C+TX%2C+USA/@,,,,z/page:{}?view=l".format(page))
    search = json.loads(request_url(url))
    return search

def pull_ha_property(property_id):
    """ Pulls a given ha property  """
    logging.info("Pulling property %s", property_id)
    text = request_url("https://www.homeaway.com/vacation-rental/p{}".format(property_id))
    json_begin = text.index('{"listing":{')
    json_end = text.index('\n', json_begin)
    return json.loads(text[json_begin:json_end + 1])

def property_iterator(propterty_ids):
    """ Returns a generator that pulls the property on iteration """
    for id in propterty_ids:
        try:
            yield pull_ha_property(id)
        except Exception as e:
            logging.exception(e)
        time.sleep(2)

def save_properties(file, property_ids):
    tmpfile = file + ".tmp"
    store = {}
    if os.path.isfile(file):
        logging.info("Reading past results from %s", file)
        with open(file, "r") as f:
            store = json.loads(f.read())
    
    duplicates = [pids for pids in property_ids if pids in store]
    property_ids = [pids for pids in property_ids if pids not in duplicates]

    logging.info("skipping properties %s", duplicates)

    for property in property_iterator(property_ids):
        store[property["listing"]["propertyId"]] = property
        with open(tmpfile, "w") as f:
            json.dump(store, f)
        os.rename(tmpfile, file)
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Graps info on homeaway propertys")
    parser.add_argument("listings", help="File containing the listings to pull")
    parser.add_argument("file_store", help="File to save progress to")

    args = parser.parse_args()
    with open(args.listings, "r") as f:
        regex = r"^https://www.homeaway.com/vacation-rental/p([0-9]+)"
        listings = [re.match(regex, l).group(1) for l in f.read().split() if re.match(regex, l) is not None]

    save_properties(args.file_store, listings)

