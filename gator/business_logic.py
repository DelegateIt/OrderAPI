from gator import config, auth
from gator.models import Model, Customer, Delegator, Transaction, TFields, DFields, delegators,\
                         Message, MFields, CFields
from gator.common import Errors, TransactionStates, Platforms, GatorException
from gator import payment, service

def create_transaction(attributes={}):
    if not Transaction.MANDATORY_KEYS <= set(attributes):
        raise GatorException(Errors.DATA_NOT_PRESENT)
    elif attributes[TFields.CUSTOMER_PLATFORM_TYPE] not in Platforms.VALID_PLATFORMS:
        raise GatorException(Errors.INVALID_PLATFORM)

    # Create a new transaction
    transaction = Transaction.create_new(attributes)
    customer_token = auth.generate_token(transaction[TFields.CUSTOMER_UUID], auth.UuidType.CUSTOMER)
    transaction[TFields.PAYMENT_URL] = payment.create_url(transaction[TFields.UUID], customer_token)

    if not transaction.create():
        raise GatorException(Errors.CONSISTENCY_ERROR)

    # Send a text to all of the delegators
    for delegator in delegators.scan():
         service.sms.send_msg(
            body="ALERT: New transaction",
            to=delegator[DFields.PHONE_NUMBER])

    return transaction

def update_transaction(transaction_uuid, attributes={}):
    # This function should only be used to update the following fields
    if not attributes.keys() <= set([TFields.DELEGATOR_UUID, TFields.STATUS, TFields.RECEIPT]):
        raise GatorException(Errors.INVALID_DATA_PRESENT)

    transaction = Model.load_from_db(Transaction, transaction_uuid)

    # Handle possible inconsistencies with the data
    if transaction is None:
        raise GatorException(Errors.TRANSACTION_DOES_NOT_EXIST)
    elif attributes.get(TFields.STATUS) is not None and attributes[TFields.STATUS] not in TransactionStates.VALID_STATES:
        raise GatorException(Errors.INVALID_DATA_PRESENT)
    elif TFields.RECEIPT in attributes and TFields.RECEIPT in transaction\
            and "stripe_charge_id" in transaction[TFields.RECEIPT]:
        raise GatorException(Errors.TRANSACTION_ALREADY_PAID)

    # Update the transaction with the new data
    transaction.update(attributes)

    if not transaction.save():
        raise GatorException(Errors.CONSISTENCY_ERROR)

def send_message(transaction, message, from_customer, mtype):
    message = Message(
        from_customer=from_customer,
        content=message,
        mtype=mtype)

    transaction.add_message(message)

    if not transaction.save():
        raise GatorException(Errors.CONSISTENCY_ERROR)

    # Handle logic for messages sent via SMS
    if transaction[TFields.CUSTOMER_PLATFORM_TYPE] == Platforms.SMS:
        customer = Model.load_from_db(Customer, transaction[TFields.CUSTOMER_UUID])
        if from_customer:
            # If the message was sent by the customer on SMS send them a confirmation
            service.sms.send_msg(
                body=config.CONFIRMATION_MESSAGE,
                to=customer[CFields.PHONE_NUMBER])
        elif not from_customer:
            # If the message was sent by the delegator send an SMS to the customer
            service.sms.send_msg(
                body=message.content,
                to=customer[CFields.PHONE_NUMBER])

    # Notify the delegator that there is a new message
    if from_customer and "delegator_uuid" in transaction:
        delegator = Model.load_from_db(Delegator, transaction[TFields.DELEGATOR_UUID])
        service.sms.send_msg(to=delegator[DFields.PHONE_NUMBER], body="ALERT: New messages")

    return message
