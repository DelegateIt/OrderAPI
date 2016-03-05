import nose
import stripe
from gator import apiclient
from endpoint.rest import RestTest

# "service" initializes stripe with the correct api key and version
import gator.core.service

class PaymentTest(RestTest):

    def setUp(self):
        apiclient.clear_database()
        self.customer_uuid = apiclient.create_customer("A", "B",
                fbuser_id="1", fbuser_token="")["uuid"]

    def generate_card_token(self):
        return stripe.Token.create(
            card={
                "number": '4242424242424242',
                "exp_month": 12,
                "exp_year": 2020,
                "cvc": '123'
        })

    def add_card(self):
        token = self.generate_card_token()
        rsp = apiclient.add_payment_card(self.customer_uuid, token.id)
        self.assertResponse(0, rsp)
        return rsp["card"], token

    def test_charge_card(self):
        (card, _) = self.add_card()
        transaction_uuid1 = apiclient.create_transaction(self.customer_uuid, "ios")["uuid"]

        # receipt not saved
        self.assertResponse(18,
                apiclient.charge_transaction_payment(transaction_uuid1, card["id"]))
        apiclient.update_transaction(transaction_uuid1, receipt={
            "total": 100,
            "items": [{
                "Pizza": 90
            }]
        })
        rsp1 = apiclient.charge_transaction_payment(transaction_uuid1, card["id"])
        self.assertResponse(0, rsp1)
        self.assertEqual(rsp1["charge"]["id"],
                apiclient.get_transaction(transaction_uuid1)["transaction"]["receipt"]["stripe_charge_id"])
        # transaction already paid
        self.assertResponse(7,
                apiclient.charge_transaction_payment(transaction_uuid1, card["id"]))

        transaction_uuid2 = apiclient.create_transaction(self.customer_uuid, "sms")["uuid"]
        apiclient.update_transaction(transaction_uuid2, receipt={
            "total": 100,
            "items": [{
                "Pizza": 90
            }]
        })
        token = self.generate_card_token()
        rsp2 = apiclient.charge_transaction_payment(transaction_uuid2, token.id, "noreply@gmail.com")
        self.assertResponse(0, rsp2)
        self.assertEqual(rsp2["charge"]["id"],
                apiclient.get_transaction(transaction_uuid2)["transaction"]["receipt"]["stripe_charge_id"])

        customer = apiclient.get_customer(self.customer_uuid)["customer"]
        self.assertEqual("noreply@gmail.com", customer["email"])
        self.assertEqual(card["customer"], customer["stripe_id"])

    def test_delete_card(self):
        (card, _) = self.add_card()
        self.assertResponse(0, apiclient.delete_payment_card(self.customer_uuid, card["id"]))
        self.assertEqual(0, len(apiclient.get_payment_cards(self.customer_uuid)["cards"]))

    def test_get_cards(self):
        (card1, _) = self.add_card()
        rsp = apiclient.get_payment_cards(self.customer_uuid)
        self.assertTrue(card1 in rsp["cards"])
        self.assertResponse(0, rsp)

        (card2, _) = self.add_card()
        rsp = apiclient.get_payment_cards(self.customer_uuid)
        self.assertResponse(0, rsp)
        self.assertTrue(card1 in rsp["cards"])
        self.assertTrue(card2 in rsp["cards"])

    def test_add_cards(self):
        (card, token) = self.add_card()
        self.assertEqual(token.card.id, card["id"])
