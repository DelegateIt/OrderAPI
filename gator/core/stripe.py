import logging
import urllib.parse
import stripe

import gator.config as config
import gator.core.service as service

from gator.core.common import GatorException, Errors
from gator.core.models import Model, TFields, RFields, Customer, CFields


def create_url(transaction_uuid, token):
    args = {
        "token": token,
        "transaction": transaction_uuid,
        "host": config.store["api_host"]["name"] + ":" +
                str(config.store["api_host"]["recv_port"])
    }
    long_url = '%s#?%s' % \
            (config.store["stripe"]["payment_url"],
            urllib.parse.urlencode(args))
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

    try:
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
    except stripe.error.CardError as e:
        raise GatorException(Errors.STRIPE_ERROR, str(e))

    transaction[TFields.RECEIPT][RFields.STRIPE_CHARGE_ID] = stripe_charge.id
    logging.info("Charged transaction %s with charge_id %s",
            transaction[TFields.UUID], stripe_charge.id)
    transaction.save()
    customer[CFields.STRIPE_ID] = stripe_customer.id
    customer[CFields.EMAIL] = email
    customer.save()
    return stripe_charge
