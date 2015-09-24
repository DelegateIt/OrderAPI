from flask import request

from gator import app
import gator.models as models
import gator.payment as payment
from gator.common import TransactionStates

import jsonpickle

from twilio.rest import TwilioRestClient

ACCOUNT_SID = "ACb5440a719947d5edf7d760155a39a768"
AUTH_TOKEN = "dd9b4240a96556da1abb1e49646c73f3"

@app.route('/sms/handle_sms', methods=["POST"])
def handle_sms():
    query_result = models.customers.query_2(index="phone_number-index", phone_number__eq=request.values["from"])

    customer = None
    if len(query_result) == 0:
        new_customer = models.Customer(phone_number=request.values["From"])
        models.customers.put_item(data=new_customer.get_data())

        customer = models.custoemrs.get_item(uuid=new_customer.uuid, consistent=True)
    else:
        customer = query_result[0]

    transaction = None
    if customer.get("active_transaction_uuids") is not None:
        transaction = models.transactions.get_item(uuid=customer["active_transaction_uuids"][0])
    else:
        transaction = models.Transaction(
                customer_uuid=customer["uuid"],
                status=TransactionStates.STARTED)
        transaction.payment_url = payment.create_url(transaction.uuid)

        # Add the transaction to the transaction table
        models.transactions.put_item(data=transaction.get_data())

        transaction = models.transactions.get_item(transaction.uuid, consistent=True)

    # Add the messages to the transaction
    message = models.Message(from_customer=True, content=request.values["Body"], platform_type="SMS")

    if transaction["messages"] is None:
        transaction["messages"] = []
    transaction["messages"].append(message.get_data())

    # Add the transaction to the active customer transactions
    if customer["active_transaction_uuids"] is None:
        customer["active_transaction_uuids"] = []
    customer["active_transaction_uuids"].append(transaction["uuid"])

    # Save the transaction and customer object
    transaction.partial_save()
    customer.partial_save()
