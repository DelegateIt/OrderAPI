import logging # TODO: remove later

from gator.models import Model, Customer, Delegator, Transaction
from gator.models import TFields
from gator.common import Errors, TransactionStates

def create_transaction(attributes={}):
    if not Transaction.MANDATORY_KEYS <= set(attributes):
        return False, None, Errors.DATA_NOT_PRESENT

    # Create a new transaction
    transaction = Transaction.create_new(attributes)

    # Load the customer associated with the transaction
    # NOTE: a customer must always be initially associated with the transaction
    customer = Model.load_from_db(Customer, attributes[TFields.CUSTOMER_UUID])
    if customer is None:
        return False, None, Errors.CUSTOMER_DOES_NOT_EXIST

    customer.add_transaction(transaction)

    delegator = None
    if attributes.get(TFields.DELEGATOR_UUID) is not None:
        delegator = Model.load_from_db(Delegator, attributes[TFields.DELEGATOR_UUID])
        if delegator is None:
            return False, None, Errors.DELEGATOR_DOES_NOT_EXIST

        delegator.add_transaction(transaction)

    # Check to see if all models were saved correctly
    # NOTE: failure implies inconsistent result
    if not transaction.create() or not customer.save() or \
            (delegator is not None and not delegator.save()):
        return False, None, Errors.CONSISTENCY_ERROR

    return True, transaction, None

def update_transaction(transaction_uuid, attributes={}):
    # This function should only be used to update the following fields
    if not attributes.keys() <= set([TFields.DELEGATOR_UUID, TFields.STATUS, TFields.RECEIPT]):
        return False, Errors.INVALID_DATA_PRESENT

    transaction = Model.load_from_db(Transaction, transaction_uuid)
    customer = Model.load_from_db(Customer, transaction[TFields.CUSTOMER_UUID])
    delegator = Model.load_from_db(Delegator, transaction[TFields.DELEGATOR_UUID])
    new_delegator = Model.load_from_db(Delegator, attributes.get(TFields.DELEGATOR_UUID))

    # Handle possible inconsistencies with the data
    if transaction is None:
        return False, Errors.TRANSACTION_DOES_NOT_EXIST
    elif attributes.get(TFields.STATUS) is not None and attributes[TFields.STATUS] not in TransactionStates.VALID_STATES:
        return False, Errors.INVALID_DATA_PRESENT
    elif TFields.RECEIPT in attributes and "stripe_charge_id" in transaction[TFields.RECEIPT]:
        return False, Errors.TRANSACTION_ALREADY_PAID
    elif customer is None:
        return False, Errors.CUSTOMER_DOES_NOT_EXIST

    # Update the customer data if the transaction state has changed from active to inactive or v.v.
    orig_is_active = transaction[TFields.STATUS] in TransactionStates.ACTIVE_STATES
    new_is_active = orig_is_active if attributes.get(TFields.STATUS) is None \
            else attributes[TFields.STATUS] in TransactionStates.ACTIVE_STATES

    # Update the transaction with the new data
    transaction.update(attributes)

    if orig_is_active == (not new_is_active):
        # A transaction will always have a customer
        customer.update_transaction_status(transaction)

        # Only update the delegator if one has been assigned to the transaction
        if delegator is not None:
            delegator.update_transaction_status(transaction)

    # Update delegator if a new one was assigned
    if new_delegator is not None:
        new_delegator.add_transaction(transaction)

        # Remove the transaction from the old delegator
        if delegator is not None:
            delegator.remove_transaction(transaction)

    # Check to see if all models were saved correctly
    # NOTE: failure implies inconsistent result
    t_saved = transaction.save()
    c_saved = customer.save()
    d_saved = True if delegator is None else delegator.save()
    nd_saved = True if new_delegator is None else new_delegator.save()

    if not (t_saved and c_saved and d_saved and nd_saved):
        return False, Errors.CONSISTENCY_ERROR

    return True, None
