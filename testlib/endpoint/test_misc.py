from gator import apiclient
from endpoint.rest import RestTest

class QuickOrdersTest(RestTest):
    def test(self):
        rsp = apiclient.get_quickorders()
        self.assertResponse(0, rsp)
        self.assertNotEqual(0, len(rsp["quickorders"]))

class SendGreetingTest(RestTest):
    def test(self):
        self.assertResponse(0, apiclient.send_greeting("15555551234"))
