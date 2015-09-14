import logging
import stripe
from flask import request, render_template

import gator.models
from gator import app

stripe.api_key = "sk_test_WYJIBAm8Ut2kMBI2G6qfEbAH"

class PaymentException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

def get_chargeable_transaction(transaction_uuid):
    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        raise PaymentException("Transaction does not exist")
    db_transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)
    if "receipt" not in db_transaction:
        raise PaymentException("The transaction has not been finalized")
    if "stripe_charge_id" in db_transaction['receipt']:
        raise PaymentException("The transaction has already been paid for")
    return db_transaction

def calculate_total(receipt):
    amount = 0
    for item in receipt['items']:
        amount += item['cents']
    return amount

def charge_transaction(transaction_uuid, stripe_token, email):
    #TODO email receipt
    db_transaction = get_chargeable_transaction(transaction_uuid)
    db_customer = gator.models.customers.get_item(uuid=db_transaction['customer_uuid'])

    stripe_customer = stripe.Customer.create(
        source=stripe_token,
        description="Paid via link",
        email=email
    )

    stripe_charge = stripe.Charge.create(
        amount=calculate_total(db_transaction['receipt']), #in cents
        currency="usd",
        customer=stripe_customer.id
    )

    db_customer['stripe_id'] = stripe_customer.id
    db_customer['email'] = email
    db_customer.save()
    db_transaction['receipt']['stripe_charge_id'] = stripe_charge.id
    db_transaction.save()

@app.route('/core/payment/uiform/<transaction_uuid>', methods=['GET'])
def ui_form(transaction_uuid):
    try:
        transaction = get_chargeable_transaction(transaction_uuid)
        amount = calculate_total(transaction['receipt'])
        return render_template('payment.html', uuid=transaction_uuid, amount=amount, total=float(amount)/100.0,
                items=transaction['receipt']['items'], notes=transaction['receipt']['notes'])
    except Exception as e:
        logging.exception(e)
        return render_template('payment-error.html', message=str(e)), 500

@app.route('/core/payment/uicharge/<transaction_uuid>', methods=['POST'])
def ui_charge(transaction_uuid):
    try:
        email = request.form['stripeEmail']
        token = request.form['stripeToken']
        charge_transaction(transaction_uuid, token, email)
        return render_template('payment-success.html')
    except stripe.error.CardError as e:
        return render_template('payment-error.html', message=str(e)), 500
    except Exception as e:
        logging.exception(e)
        return render_template('payment-error.html', message=str(e)), 500

