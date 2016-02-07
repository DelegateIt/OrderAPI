import jsonpickle
import logging
import urllib.parse
import stripe
from flask import request

import gator.service as service
import gator.config as config
from gator.common import GatorException, Errors
from gator.auth import authenticate, Permission, validate
from gator.models import Model, Transaction, TFields, RFields, Customer, CFields
from gator.flask import app

def create_url(transaction_uuid, token):
    host = config.store["api_host"]["name"]
    port = config.store["api_host"]["recv_port"]
    args = {
        "token": token,
        "transaction": transaction_uuid,
        "host": host + ":" + str(port)
    }
    long_url = 'http://%s:%s/static/payment.html#?%s' % \
            (host, port, urllib.parse.urlencode(args))
    return service.shorturl.shorten_url(long_url)

def get_stripe_customer(customer, save_on_create=True):
    if CFields.STRIPE_ID in customer:
        return stripe.Customer.retrieve(customer[CFields.STRIPE_ID])
    else:
        stripe_customer = stripe.Customer.create(
                metadata={"gator_customer_uuid": customer[CFields.UUID]})
        customer[CFields.STRIPE_ID] = stripe_customer.id
        if save_on_create:
            customer.save()
            stripe_customer.save()
        return stripe_customer

def get_cards(customer_uuid):
    customer = Model.load_from_db(Customer, customer_uuid)
    stripe_customer = get_stripe_customer(customer)
    return stripe_customer.sources.data

def add_card(customer_uuid, stripe_token):
    customer = Model.load_from_db(Customer, customer_uuid)
    stripe_customer = get_stripe_customer(customer)
    return stripe_customer.sources.create(source=stripe_token)

def delete_card(customer_uuid, stripe_card_id):
    customer = Model.load_from_db(Customer, customer_uuid)
    stripe_customer = get_stripe_customer(customer)
    if not stripe_customer.sources.retrieve(stripe_card_id).delete().deleted:
        raise GatorException(Errors.STRIPE_ERROR)

def new_transaction_charge(transaction, stripe_source, email=None):
    # TODO: email receipt
    if TFields.RECEIPT not in transaction:
        raise GatorException(Errors.RECEIPT_NOT_SAVED)
    if RFields.STRIPE_CHARGE_ID in transaction[TFields.RECEIPT]:
        raise GatorException(Errors.TRANSACTION_ALREADY_PAID)

    customer = Model.load_from_db(Customer, transaction[TFields.CUSTOMER_UUID])
    stripe_customer = get_stripe_customer(customer, save_on_create=False)

    stripe_customer.source = stripe_source
    stripe_customer.email = email
    stripe_customer.save()

    stripe_charge = stripe.Charge.create(
        amount=transaction[TFields.RECEIPT][RFields.TOTAL], # in cents
        currency="usd",
        customer=stripe_customer.id,
        metadata={"gator_transaction_uuid": transaction[TFields.UUID]}
    )

    transaction[TFields.RECEIPT][RFields.STRIPE_CHARGE_ID] = stripe_charge.id
    logging.info("Charged transaction %s with charge_id %s",
            transaction[TFields.UUID], stripe_charge.id)
    transaction.save()
    customer[CFields.STRIPE_ID] = stripe_customer.id
    customer[CFields.EMAIL] = email
    customer.save()
    return stripe_charge

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
