import nose
from gator import apiclient
from endpoint.rest import RestTest

class NotifyTest(RestTest):

    def setUp(self):
        apiclient.clear_database()


    def test_notifier(self):
        self.assertEqual(0, len(apiclient.get_notify_handlers()["handlers"]))
        rsp = apiclient.add_notify_handler(8060)
        self.assertTrue("expires" in rsp["handler"] and "ip_address" in rsp["handler"])
        rsp = apiclient.get_notify_handlers()
        self.assertEquals(1, len(rsp["handlers"]))
        self.assertTrue("expires" in rsp["handlers"][0] and "ip_address" in rsp["handlers"][0])
        self.assertEqual(8060, rsp["handlers"][0]["port"])

        #Should do nothing since the previous handler is not expired
        self.assertResponse(0, apiclient.purge_notify_handlers())
        self.assertEqual(1, len(apiclient.get_notify_handlers()["handlers"]))


if __name__ == "__main__":
    nose.main(defaultTest=__name__)
