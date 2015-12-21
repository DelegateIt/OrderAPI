from flask import request

from gator.flask import app
import gator.service as service
import gator.models as models
import gator.common as common
import gator.business_logic as bl
from gator.models import Customer, CFields, TFields, Model, Transaction, DFields, MTypes
from gator.common import TransactionStates, Platforms
from gator.auth import validate_permission, authenticate, Permission, validate_token

import jsonpickle

@app.route('/sms/handle_sms', methods=["POST"])
def handle_sms():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.API_SMS])

    # TODO the query_count can be optimized out
    query_result = models.customers.query_2(index="phone_number-index", phone_number__eq=request.values["From"], limit=1)
    query_count = models.customers.query_count(index="phone_number-index", phone_number__eq=request.values["From"], limit=1)

    customer = None
    if query_count == 0:
        # If no customer exists create a new one
        customer = Customer.create_new({
            CFields.PHONE_NUMBER: request.values["From"]
        })
        customer.save()
    else:
        customer = Customer(query_result.next())

    # Find the SMS transaction if it exists
    transaction = None
    if customer[CFields.A_TRANS_UUIDS] is not None:
        for transaction_uuid in customer[CFields.A_TRANS_UUIDS]:
            cur_transaction = Model.load_from_db(Transaction, transaction_uuid)
            if cur_transaction[TFields.CUSTOMER_PLATFORM_TYPE] == Platforms.SMS:
                transaction = cur_transaction
                break

    # Create a new one doesn't exist
    if transaction is None:
        # Create a new transaction if none exists
        success, transaction, error = bl.create_transaction({
            TFields.CUSTOMER_UUID: customer[CFields.UUID],
            TFields.CUSTOMER_PLATFORM_TYPE: Platforms.SMS
        })
        if error is not None:
            return common.error_to_json(error)

        # Send a text to all of the delegators
        for delegator in models.delegators.scan():
            service.sms.send_msg(
                body="ALERT: New transaction from %s" % customer["phone_number"],
                to=delegator["phone_number"])

    # Add the messages to the transaction
    message = models.Message(from_customer=True, content=request.values["Body"], mtype=MTypes.TEXT.value)
    transaction.add_message(message)

    if not (customer.save() and transaction.save()):
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    if "delegator_uuid" in transaction:
        delegator = models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)
        service.sms.send_msg(to=delegator["phone_number"], body="ALERT: New message from %s" % request.values["From"])

    return jsonpickle.encode({"result": 0})
