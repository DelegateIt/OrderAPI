import nose
import unittest
import subprocess
import sys
from gator import apiclient

# This just setups the environment so nodejs can run it's test
class NotifyTest(unittest.TestCase):

    def setUp(self):
        apiclient.clear_database()
        cid = apiclient.create_customer("asdf", "sadfs", "15555555551")["uuid"]
        self.transaction_uuid = apiclient.create_transaction(cid, "sms")["uuid"]

    def test_end_2_end(self):
        # Nodejs should perform the actual test
        # subprocess.check_call(["nodejs", "notifier/test.js", self.transaction_uuid], stdout=sys.stdout)
        process = subprocess.Popen(["node", "test.js", self.transaction_uuid], stdout=subprocess.PIPE)
        process.wait()
        print(process.stdout.read().decode("UTF-8").strip())
        self.assertEquals(process.returncode, 0)
