import stripe
from flask import request

import gator.models
from gator import app

stripe.api_key = "sk_test_WYJIBAm8Ut2kMBI2G6qfEbAH"

@app.route('/core/payment/uiform/<transaction_uuid>', methods=['GET'])
def gen_ui_form(transaction_uuid):
    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        raise Exception("Transaction does not exist")
    transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)._data
    if "receipt" not in transaction:
        raise Exception("Transaction has not been finalized")
    if transaction['receipt']['paid_for']:
        raise Exception("Transaction has already been paid for")
    amount = 0
    for item in transaction['receipt']['items']:
        amount += item['cents']

    #TODO display 'already paid for' page if transaction is paid for
    #TODO move this to seperate file and make it look pretty
    page = '''
        <form action="/core/payment/uicharge/{uuid}" method="POST">
            <script
                src="https://checkout.stripe.com/checkout.js" class="stripe-button"
                data-key="pk_test_ZoK03rN4pxc2hfeYTzjByrdV"
                data-name="DelegateIt"
                data-description="Your personal concierge service"
                data-amount="{amount}"
                data-locale="auto">
            </script>
            <input type="hidden" name="amount" value="{amount}">
        </form>
    '''.format(uuid=transaction_uuid, amount=amount)
    return page

@app.route('/core/payment/uicharge/<transaction_uuid>', methods=['POST'])
def ui_charge(transaction_uuid):
    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        raise Exception("Transaction does not exist")
    #TODO email receipt
    #TODO handle all stripe errors
    email = request.form['stripeEmail']
    amount = int(request.form['amount'])
    db_transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)
    db_customer = gator.models.customers.get_item(uuid=db_transaction._data['customer_uuid'])
    if "receipt" not in db_transaction._data:
        raise Exception("Transaction has not been finalized")
    if db_transaction._data['receipt']['paid_for']:
        raise Exception("Transaction has already been paid for")

    stripe_customer = stripe.Customer.create(
        source=request.form['stripeToken'],
        description="Paid via link",
        email=email
    )

    stripe.Charge.create(
        amount=amount, #in cents
        currency="usd",
        customer=stripe_customer.id
    )

    db_customer._data['stripe_id'] = stripe_customer.id
    db_customer._data['email'] = email
    db_customer.save()
    db_transaction._data['receipt']['paid_for'] = True
    db_transaction.save()
    return "You were successfully charged ${}".format(amount / 100.0)

