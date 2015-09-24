from flask import request

from gator import app
import gator.models as models
import gator.payment as payment
from gator.common import TransactionStates

import jsonpickle

@app.route('/sms/handle_sms', methods=["POST"])
def handle_sms():
    query_result = models.customers.query_2(index="phone_number-index", phone_number__eq=request.values["From"])
    query_count = models.customers.query_count(index="phone_number-index", phone_number__eq=request.values["From"])

    customer = None
    if query_count == 0:
        new_customer = models.Customer(phone_number=request.values["From"])
        models.customers.put_item(data=new_customer.get_data())

        customer = models.customers.get_item(uuid=new_customer.uuid, consistent=True)
    else:
        customer = query_result.next()

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

        transaction = models.transactions.get_item(uuid=transaction.uuid, consistent=True)

    # Add the messages to the transaction
    message = models.Message(from_customer=True, content=request.values["Body"], platform_type="SMS")

    if transaction["messages"] is None:
        transaction["messages"] = []
    transaction["messages"].append(message.get_data())

    # Add the transaction to the active customer transactions
    if customer["active_transaction_uuids"] is None:
        customer["active_transaction_uuids"] = []

    if transaction["uuid"] not in customer["active_transaction_uuids"]:
        customer["active_transaction_uuids"].append(transaction["uuid"])

    # Save the transaction and customer object
    transaction.partial_save()
    customer.partial_save()

    return '{"result": 0}'
