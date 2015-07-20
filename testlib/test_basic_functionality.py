import unittest
import requests, json
import subprocess, os, signal
import MySQLdb
import gc

db = MySQLdb.connect(host="localhost",
                     user="root",
                     passwd="default",
                     db="DelegateItDB")

cur = db.cursor()


class TestBasicRestFunctionality(unittest.TestCase):
    """@classmethod
    def setUpClass(cls):
        # Start up the rest_handler
        cls.proc = subprocess.Popen(["python", "../rest_handler.py"],
            shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)"""

    @classmethod
    def tearDownClass(cls):
        # Clear the db
        cur.execute("SET foreign_key_checks = 0;")
        cur.execute("TRUNCATE TABLE customers;")
        cur.execute("TRUNCATE TABLE messages;")
        cur.execute("SET foreign_key_checks = 1;")

        # Make sure connection is garbage collected
        gc.collect()

        """if cls.proc.pid is not None:
            os.kill(cls.proc.pid, signal.SIGTERM)

        # Uncomment for debugging
        if cls.proc.returncode != 0:
            stdout, stderr = cls.proc.communicate()
            stdout = cls.proc.stdout.read()
            stderr = cls.proc.stderr.read()
            print "stdout: %s\nstderr: %s" % (stdout, stderr)"""

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

        user_response_data = requests.post("http://localhost:8080/customer/%s" % phone_number, customer_json_data).json()
        message_response_data = requests.post("http://localhost:8080/send_message/%s" % phone_number, message_json_data).json()

        # Verify that responses are correct
        self.assertEquals(user_response_data["result"], 0)
        self.assertEquals(message_response_data["result"], 0)
        self.assertNotEquals(message_response_data["timestamp"], None)

        # Check the db for correct data
        cur.execute("SELECT * FROM messages;")
        query_result = cur.fetchall()

        cur.execute("SELECT * FROM messages WHERE customer_id=1"),
        query_result_2 = cur.fetchall()

        self.assertEquals(len(query_result), 1) # assert that only one message is present
        self.assertTrue("test_send_message content" in query_result[0]) # no guaranteed ordering in result
        self.assertEquals(query_result, query_result_2) # verify that data is associated correctly
