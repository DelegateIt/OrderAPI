
import unittest
import logging

logging.getLogger("boto").setLevel(logging.INFO)
logging.getLogger("requests").setLevel(logging.WARN)

class RestTest(unittest.TestCase):

    def assertResponse(self, expected_code, response, expected_keys=[]):
        self.assertEqual(response["result"], expected_code, "The expected return code did not match the actual")
        for key in expected_keys:
            self.assertTrue(key in response, "The response did not contain the `{}` key".format(key))

