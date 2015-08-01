import unittest
import re
import requests, json
import subprocess, os, signal
import psycopg2
import gc

db = psycopg2.connect(host="restservicetestdb.cwfe0qmzkgyc.us-west-2.rds.amazonaws.com",
                     port=5432,
                     user="Delegator",
                     password="WeAreDelegators99",
                     database="DelegateItDB")

cur = db.cursor()

def clear():
    # Clear the db
    """cur.execute("SET foreign_key_checks = 0;")
    kill_all_locked_processes()

    print "Finished 1"
    cur.execute("TRUNCATE TABLE messages;")
    print "next"
    kill_all_locked_processes()
    print "Finished truncate 1"

    print "finished dropping"
    cur.execute("TRUNCATE TABLE customers;")
    kill_all_locked_processes()
    cur.execute("SET foreign_key_checks = 1;")
    print "Finished all" """

    print "clear"
    #cur.execute("TRUNCATE TABLE messages;")
    #kill_all_locked_processes()
    #cur.execute("TRUNCATE TABLE customers * CASCADE;")
    try:
        cur.execute("DROP TABLE customers CASCADE;")
    except Exception as e:
        print e
        db.rollback()

    #kill_all_locked_processes()
    #kill_all_locked_processes()
    print "Finished clearing"

    #kill_all_locked_processes()
    #cur.execute("DROP DATABASE DelegateItDB")
    #print "Done dropping"
    #kill_all_locked_processes()
    #cur.execute("CREATE DATABASE DelegateItDB")


def kill_all_locked_processes():
    # Kill all processes that are locked on the mutex
    """cur.execute("SHOW PROCESSLIST;")
    query_result = cur.fetchall()

    for row in query_result:
        if re.search("Waiting.*lock", row[6]):
            print row
            cur.execute("KILL %s" % row[0])
        else:
            print "<SAFE> %s" % str(row)"""

    cur.execute("SELECT relation::regclass, * FROM pg_locks WHERE NOT GRANTED;")
    query_result = cur.fetchall()

    for row in query_result:
        print row
        cur.execute("SELECT pg_cancel_backend(%s);" % row[12]);


class TestBasicRestFunctionality(unittest.TestCase):
    def setUp(self):
        print "setting up"
        clear()
        print "done setting up"

        # Start up the rest_handler
        """cls.proc = subprocess.Popen(["python", "../rest_handler.py"]
            shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)"""

    def tearDown(self):
        clear()

        # Close connections
        cur.close()
        db.close()

        """if cls.proc.pid is not None:
            os.kill(cls.proc.pid, signal.SIGTERM)

        # Uncomment for debugging
        if cls.proc.returncode != 0:
            stdout, stderr = cls.proc.communicate()
            stdout = cls.proc.stdout.read()
            stderr = cls.proc.stderr.read()
            print "stdout: %s\nstderr: %s" % (stdout, stderr)"""

    @classmethod
    def tearDownClass(cls):
        # Make sure connection is garbage collected
        gc.collect()

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
