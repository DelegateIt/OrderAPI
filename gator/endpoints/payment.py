import jsonpickle
from flask import request

from gator.flask import app
from gator.core.common import GatorException, Errors
from gator.core.auth import authenticate, Permission, validate
from gator.core.models import Model, Transaction, TFields
from gator.core.stripe import new_transaction_charge, add_card, delete_card,\
                              get_cards

@app.route('/payment/charge/<transaction_uuid>', methods=['POST'])
def post_payment_charge(transaction_uuid):
    transaction = Model.load_from_db(Transaction, transaction_uuid)
    if transaction is None:
        raise GatorException(Errors.TRANSACTION_DOES_NOT_EXIST)
    validate(request.args.get("token", ""), [Permission.CUSTOMER_OWNER],
            transaction[TFields.CUSTOMER_UUID])

    req = jsonpickle.decode(request.data.decode("utf-8"))
    if "stripe_source" not in req:
        raise GatorException(Errors.DATA_NOT_PRESENT)
    stripe_source = req["stripe_source"]
    email = req.get("email")

    stripe_charge = new_transaction_charge(transaction, stripe_source, email)
    return jsonpickle.encode({"result": 0, "charge": stripe_charge})


@app.route('/payment/card/<customer_uuid>', methods=['GET'])
@authenticate([Permission.CUSTOMER_OWNER])
def get_payment_card(customer_uuid):
    cards = get_cards(customer_uuid)
    return jsonpickle.encode({"result": 0, "cards": cards})

@app.route('/payment/card/<customer_uuid>', methods=['POST'])
@authenticate([Permission.CUSTOMER_OWNER])
def post_payment_card(customer_uuid):
    req = jsonpickle.decode(request.data.decode("utf-8"))
    if "stripe_token" not in req:
        raise GatorException(Errors.DATA_NOT_PRESENT)
    card = add_card(customer_uuid, req["stripe_token"])
    return jsonpickle.encode({"result": 0, "card": card})

@app.route('/payment/card/<customer_uuid>', methods=['DELETE'])
@authenticate([Permission.CUSTOMER_OWNER])
def delete_payment_card(customer_uuid):
    req = jsonpickle.decode(request.data.decode("utf-8"))
    if "stripe_card_id" not in req:
        raise GatorException(Errors.DATA_NOT_PRESENT)
    delete_card(customer_uuid, req["stripe_card_id"])
    return jsonpickle.encode({"result": 0})
