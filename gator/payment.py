import jsonpickle
import logging
import urllib.parse
import stripe
from flask import request, render_template, redirect

import gator.service as service

import gator.common as common
import gator.config as config
from gator.common import GatorException, Errors
from gator.auth import authenticate, Permission, validate
from gator.models import Model, Transaction, TFields, RFields, Customer, CFields
from gator.flask import app

class PaymentException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def get_chargeable_transaction(transaction_uuid, enforce_finalized=True):
    transaction = Model.load_from_db(Transaction, transaction_uuid)

    if transaction is None:
        raise PaymentException("Transaction does not exist")
    elif enforce_finalized and transaction[TFields.RECEIPT] is None:
        raise PaymentException("The transaction has not been finalized")

    return transaction

def charge_transaction(transaction_uuid, stripe_source, email=None):
    # TODO: email receipt
    transaction = get_chargeable_transaction(transaction_uuid)

    if RFields.STRIPE_CHARGE_ID in transaction[TFields.RECEIPT]:
        return # Transaction has already been paid for

    customer = Model.load_from_db(Customer, transaction[TFields.CUSTOMER_UUID])

    if customer[CFields.STRIPE_ID] is not None:
        stripe_customer = stripe.Customer.retrieve(customer[CFields.STRIPE_ID])
        stripe_customer.source = stripe_source
        stripe_customer.email = email
        stripe_customer.save()
    else:
        stripe_customer = stripe.Customer.create(
            source=stripe_source,
            description="Paid via link",
            email=email,
            metadata={
                "gator_customer_uuid": customer["uuid"],
            }
        )

    stripe_charge = stripe.Charge.create(
        amount=transaction[TFields.RECEIPT][RFields.TOTAL], # in cents
        currency="usd",
        customer=stripe_customer.id
    )

    customer[CFields.STRIPE_ID] = stripe_customer.id
    customer[CFields.EMAIL] = email
    customer.save()
    transaction[TFields.RECEIPT][RFields.STRIPE_CHARGE_ID] = stripe_charge.id
    transaction.save()

def generate_redirect(success, message=None):
    args = {"success": success}
    if message is not None:
        args["message"] = message
    url = "/payment/uistatus?" + urllib.parse.urlencode(args)
    return redirect(url, code=302)

def create_url(transaction_uuid, token, use_test_api):
    host = config.store["api_host"]["name"]
    port = config.store["api_host"]["recv_port"]
    args = {
        "token": token,
        "transaction": transaction_uuid,
        "test": use_test_api
    }
    long_url = 'http://%s:%s/payment/uiform/%s?%s' % \
            (host, port, transaction_uuid, urllib.parse.urlencode(args))
    return service.shorturl.shorten_url(long_url)

@app.route('/payment/uiform/<transaction_uuid>', methods=['GET'])
def ui_form(transaction_uuid):
    try:
        transaction = get_chargeable_transaction(transaction_uuid, enforce_finalized=False)
        if transaction[TFields.RECEIPT] is None:
            return render_template('payment-error.html', message="The receipt has not been saved. Please contact your delegator"), 500
        if RFields.STRIPE_CHARGE_ID in transaction[TFields.RECEIPT]:
            return generate_redirect(True)
        else:
            amount = transaction[TFields.RECEIPT][RFields.TOTAL]
            notes = "" if RFields.NOTES not in transaction[TFields.RECEIPT] else transaction[TFields.RECEIPT][RFields.NOTES]
            return render_template('payment.html', uuid=transaction_uuid, amount=amount, total=float(amount)/100.0,
                    items=transaction[TFields.RECEIPT][RFields.ITEMS], notes=notes,
                    stripe_pub_key=config.store["stripe"]["public_key"])
    except Exception as e:
        logging.exception(e)
        return generate_redirect(False, str(e))

@app.route('/payment/uicharge/<transaction_uuid>', methods=['POST'])
def ui_charge(transaction_uuid):
    try:
        email = request.form['stripeEmail']
        token = request.form['stripeToken']
        charge_transaction(transaction_uuid, token, email)
        return generate_redirect(True)
    except stripe.error.CardError as e:
        return generate_redirect(False, str(e))
    except Exception as e:
        logging.exception(e)
        return generate_redirect(False, str(e))

@app.route('/payment/uistatus/', methods=['GET'])
def ui_status():
    try:
        success = request.args["success"] == "True"
        if success:
            return render_template('payment-success.html')
        else:
            message = request.args["message"]
            return render_template('payment-error.html', message=message), 500
    except Exception as e:
        logging.exception(e)
        return render_template('payment-error.html', message=str(e)), 500

def get_stripe_customer(customer, save_on_create=True):
    if CFields.STRIPE_ID in customer:
        return stripe.Customer.retrieve(customer[CFields.STRIPE_ID])
    else:
        stripe_customer = stripe.Customer.create(
                metadata={"gator_customer_uuid": customer["uuid"]})
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
