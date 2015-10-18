import json
import logging
import urllib.parse
import stripe
from flask import request, render_template, redirect

import gator.service
import gator.models
import gator.common
from gator import app

class PaymentException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def get_chargeable_transaction(transaction_uuid):
    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        raise PaymentException("Transaction does not exist")
    db_transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)
    if "receipt" not in db_transaction:
        raise PaymentException("The transaction has not been finalized")
    return db_transaction

def charge_transaction(transaction_uuid, stripe_token, email):
    #TODO email receipt
    db_transaction = get_chargeable_transaction(transaction_uuid)
    if "stripe_charge_id" in db_transaction['receipt']:
        return #It has already been paid
    db_customer = gator.models.customers.get_item(uuid=db_transaction['customer_uuid'])

    if "stripe_id" in db_customer:
        stripe_customer = stripe.Customer.retrieve(db_customer["stripe_id"])
        stripe_customer.source = stripe_token
        stripe_customer.email = email
        stripe_customer.save()
    else:
        stripe_customer = stripe.Customer.create(
            source=stripe_token,
            description="Paid via link",
            email=email,
            metadata={
                "gator_customer_uuid": db_customer["uuid"],
            }
        )

    stripe_charge = stripe.Charge.create(
        amount=db_transaction['receipt']['total'], #in cents
        currency="usd",
        customer=stripe_customer.id
    )

    db_customer['stripe_id'] = stripe_customer.id
    db_customer['email'] = email
    db_customer.partial_save()
    db_transaction['receipt']['stripe_charge_id'] = stripe_charge.id
    db_transaction.partial_save()

def generate_redirect(success, message=None):
    args = {"success": success}
    if message is not None:
        args["message"] = message
    url = "/payment/uistatus?" + urllib.parse.urlencode(args)
    return redirect(url, code=302)

def create_url(transaction_uuid):
    host = gator.config.store["api_host"]["name"]
    long_url = 'http://%s/payment/uiform/%s' % (host, transaction_uuid)
    return gator.service.shorturl.shorten_url(long_url)

@app.route('/payment/uiform/<transaction_uuid>', methods=['GET'])
def ui_form(transaction_uuid):
    try:
        transaction = get_chargeable_transaction(transaction_uuid)
        if "stripe_charge_id" in transaction['receipt']:
            return generate_redirect(True)
        else:
            amount = transaction['receipt']['total']
            notes = "" if "notes" not in transaction['receipt'] else transaction['receipt']['notes']
            return render_template('payment.html', uuid=transaction_uuid, amount=amount, total=float(amount)/100.0,
                    items=transaction['receipt']['items'], notes=notes,
                    stripe_pub_key=gator.config.store["stripe"]["public_key"])
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


