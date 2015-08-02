import unittest

import boto.dynamodb2
from boto.dynamodb2.table import Table

import re
import requests, json
import subprocess, os, signal

# Connection to DynamoDB
conn = boto.dynamodb2.connect_to_region(
        "us-west-2",
        aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
        aws_secret_access_key="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")

# Tables
customers = Table("DelegateIt_Customers", connection=conn)

def clear():
    for customer in customers.scan():
        customer.delete()

class TestBasicRestFunctionality(unittest.TestCase):
    def setUp(self):
        clear()

        # Start up the rest_handler
        """self.proc = subprocess.Popen(["python", "../rest_handler.py"],
            shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)"""

    def tearDown(self):
        clear()

        """if self.proc.pid is not None:
            os.kill(self.proc.pid, signal.SIGTERM)"""

        # Uncomment for debugging
        """if cls.proc.returncode != 0:
            stdout, stderr = cls.proc.communicate()
            stdout = cls.proc.stdout.read()
            stderr = cls.proc.stderr.read()
            print "stdout: %s\nstderr: %s" % (stdout, stderr)"""

    def test_create_customer(self):
        print "Testing create customer"
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        phone_number = "8176808185"

        print "Sending request to"

        customer_response_data = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()

        # Verify that the response is correct
        self.assertEquals(customer_response_data["result"], 0)

        print "done with rest stuff"

        # CHeck the db
        """cur.execute("SELECT * FROM customers")
        query_result = cur.fetchall()

        self.assertEquals(len(query_result), 1)
        self.assertTrue(set(["George", "Farcasiu"]).issubset(query_result[0]))
        """


    def test_get_customer(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        phone_number = "8176808185"

        requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()
        print "done posting"
        customer_get_response_data = requests.get("http://localhost:8080/customer/%s" % phone_number).json()
        print "get get response back"
        print customer_get_response_data

        # Verify that the response is correct
        self.assertEquals(customer_get_response_data["first_name"], "George")
        self.assertEquals(customer_get_response_data["last_name"], "Farcasiu")
        self.assertEquals(customer_get_response_data["phone_number"], phone_number)

        print "finished getting customer"

    def test_send_message(self):
        customer_json_data = json.dumps({
            "first_name": "George",
            "last_name":  "Farcasiu"
        })

        message_json_data = json.dumps({
            "platform_type": "sms",
            "content": "test_send_message content"
        })

        phone_number = "8176808185"

        customer_response_data = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()
        message_response_data = requests.post("http://localhost:8080/send_message/%s" % phone_number, message_json_data).json()

        # Verify that responses are correct
        self.assertEquals(customer_response_data["result"], 0)
        self.assertEquals(message_response_data["result"], 0)
        self.assertNotEquals(message_response_data["timestamp"], None)

        # Check the db for correct data
        """cur.execute("SELECT * FROM messages;")
        query_result = cur.fetchall()

        cur.execute("SELECT * FROM messages WHERE customer_id=1"),
        query_result_2 = cur.fetchall()

        self.assertEquals(len(query_result), 1) # assert that only one message is present
        self.assertTrue("test_send_message content" in query_result[0]) # no guaranteed ordering in result
        self.assertEquals(query_result, query_result_2) # verify that data is associated correctly"""

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBasicRestFunctionality)
    unittest.TextTestRunner(verbosity=2).run(suite)
