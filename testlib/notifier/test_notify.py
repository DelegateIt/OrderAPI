import unittest
import subprocess

# This just setups the environment so nodejs can run it's test
class NotifyTest(unittest.TestCase):

    def test_end_2_end(self):
        # Nodejs should perform the actual test
        process = subprocess.Popen(["mocha", "test.js"], stdout=subprocess.PIPE)
        process.wait()
        print(process.stdout.read().decode("UTF-8").strip())
        self.assertEquals(process.returncode, 0)
