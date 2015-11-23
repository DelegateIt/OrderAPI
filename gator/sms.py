from flask import request

from gator.flask import app
import gator.service as service
import gator.models as models
import gator.payment as payment
import gator.business_logic as bl
from gator.common import TransactionStates

import jsonpickle

@app.route('/sms/handle_sms', methods=['POST'])
def handle_sms():
    query_result = models.customers.query_2(index="phone_number-index", phone_number__eq=request.values["From"])
    query_count = models.customers.query_count(index="phone_number-index", phone_number__eq=request.values["From"])

    customer = None
    if query_count == 0:
        # If no customer exists create a new one
        customer = Customer.create_new({
            CFields.PHONE_NUMBER: request.values["From"]
        })
    else:
        customer = Customer(query_result.next())

    transaction = None
    if customer[CFields.A_TRANS_UUIDS] is None or len(customer[CFields.A_TRANS_UUIDS]) == 0:
        # Create a new transaction if none exists
        success, transaction, error = bl.create_transaction({
            TFields.CUSTOMER_UUID: customer[CFields.UUID]
        })

        # Send a text to all of the delegators
        for delegator in gator.models.delegators.scan():
            service.sms.send_msg(
                body="ALERT: New transaction from %s" % customer["phone_number"],
                to=delegator["phone_number"])
    else:
        transaction = Model.load_from_db(Transaction, customer[A_TRANS_UUIDS][0])

    # Add the messages to the transaction
    message = models.Message(from_customer=True, content=request.values["Body"], platform_type="SMS")
    transaction.add_message(message)

    if not (customer.save() and transaction.save()):
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0})
