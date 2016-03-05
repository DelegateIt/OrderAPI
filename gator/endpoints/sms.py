from flask import request

from gator.flask import app
import gator.core.models as models
import gator.logic.transactions as transactions

from gator.core.models import Model, Customer, CFields, Transaction, TFields, MTypes
from gator.core.common import TransactionStates, Platforms
from gator.core.auth import validate_permission, Permission, validate_token

import jsonpickle

def get_sms_customer(phone_number):
    query = [c for c in models.customers.query_2(index="phone_number-index",
            phone_number__eq=phone_number, limit=1)]
    if len(query) == 0:
        customer = Customer.create_new({
            CFields.PHONE_NUMBER: phone_number
        })
        customer.create()
        return customer
    else:
        customer = Customer(query[0])
        return customer

def get_sms_transaction(customer_uuid):
    query = models.transactions.query_2(
                customer_uuid__eq=customer_uuid,
                reverse=True,
                consistent=True)
    for q in query:
        if q[TFields.STATUS] != TransactionStates.COMPLETED and q[TFields.CUSTOMER_PLATFORM_TYPE] == Platforms.SMS:
            return Transaction(q)

    transaction = transactions.create_transaction({
        TFields.CUSTOMER_UUID: customer_uuid,
        TFields.CUSTOMER_PLATFORM_TYPE: Platforms.SMS
    })
    transaction.create()
    return transaction

@app.route('/sms/handle_sms', methods=["POST"])
def handle_sms():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.API_SMS])

    customer = get_sms_customer(request.values["From"])
    transaction = get_sms_transaction(customer[CFields.UUID])
    transactions.send_message(transaction, request.values["Body"], True, MTypes.TEXT)

    return jsonpickle.encode({"result": 0})
