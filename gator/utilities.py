#!/usr/bin/env python3.4
""" The misc and utility file

Put things in here that are scripts or tangential
uses of the backend
"""

from service import sms
import sys

def mass_text(body_fn, numbers_fn):
    body = open(body_fn, "r").read()

    with open(numbers_fn, "r") as cur_file:
        cur_line = cur_file.readline()
        while cur_line != "":
            sms.send_msg(cur_line, body)
            cur_line = cur_file.readline()

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
