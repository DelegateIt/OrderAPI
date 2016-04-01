from flask import request

from gator.flask import app
import gator.core.models as models
import gator.logic.transactions as transactions
import gator.config as config

from gator.core.models import Model, Customer, CFields, Transaction, TFields, MTypes
from gator.core.common import TransactionStates, Platforms
from gator.core.auth import validate_permission, Permission, validate_token
from gator.core.service import sms

import jsonpickle
import re

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

    customer_phone_number = request.values["From"]
    text_message_body = request.values["Body"]

    # Check to see if the message was a HELP message
    if re.match("^\s*HELP\s*$", text_message_body, flags=re.IGNORECASE) is not None:
        sms.send_msg(body=config.HELP_MESSAGE_1, to=customer_phone_number)
        sms.send_msg(body=config.HELP_MESSAGE_2, to=customer_phone_number)
        return jsonpickle.encode({"result": 0})

    customer = get_sms_customer(customer_phone_number)
    transaction = get_sms_transaction(customer[CFields.UUID])
    transactions.send_message(transaction, text_message_body, True, MTypes.TEXT)

    # Send the customer a confirmation message
    sms.send_msg(body=config.CONFIRMATION_MESSAGE, to=customer_phone_number)

    return jsonpickle.encode({"result": 0})

phones_greeted = set({})
@app.route("/sms/sendgreeting/<phone_number>", methods=["POST"])
def send_greeting(phone_number):
    global phones_greeted

    # Make sure we only text this number once (from this node)
    if phone_number in phones_greeted:
        raise GatorException(Errors.PERMISSION_DENIED)

    phones_greeted.add(phone_number)
    sms.send_msg(body=config.HELP_MESSAGE_1, to=phone_number)
    return jsonpickle.encode({"result": 0})
