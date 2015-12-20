import json
import logging
import urllib.parse
import stripe
from flask import request, render_template, redirect

import gator.service as service

import gator.common as common
import gator.config as config
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

def charge_transaction(transaction_uuid, stripe_token, email):
    # TODO: email receipt
    transaction = get_chargeable_transaction(transaction_uuid)

    if RFields.STRIPE_CHARGE_ID in transaction[TFields.RECEIPT]:
        return # Transaction has already been paid for

    customer = Model.load_from_db(Customer, transaction[TFields.CUSTOMER_UUID])

    if customer[CFields.STRIPE_ID] is not None:
        stripe_customer = stripe.Customer.retrieve(customer[CFields.STRIPE_ID])
        stripe_customer.source = stripe_token
        stripe_customer.email = email
        stripe_customer.save()
    else:
        stripe_customer = stripe.Customer.create(
            source=stripe_token,
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

def create_url(transaction_uuid):
    host = config.store["api_host"]["name"]
    port = config.store["api_host"]["recv_port"]
    long_url = 'http://%s:%s/payment/uiform/%s' % (host, port, transaction_uuid)
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
