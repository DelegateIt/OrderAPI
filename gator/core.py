from flask import request

import jsonpickle
import boto

import gator.service as service
import gator.models as models
import gator.common as common
import gator.config as config

from gator.flask import app
from gator.models import Model, Customer, Delegator, Transaction, Message
from gator.models import CFields, DFields, TFields, MFields
from gator.common import Errors, TransactionStates

@app.after_request
def after_request(response):
    #TODO - Important Security - replace '*' with name of the server hosting the delegator web client
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

@app.route('/')
def index():
    return "GatorRestService is up and running!"

@app.route('/core/customer', methods=['POST'])
def customer_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    if not Customer.MANDATORY_KEYS <= set(data.keys()):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    customer = Customer.create_new(data)

    if not customer.is_unique():
        return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

    # Save the customer to db
    if not customer.create():
        return common.error_to_json(Erros.CONSISTENCY_ERROR)

    # Send a text to the user if they signed up from the LandingPage
    if request.args.get('sendtext', 'false') == 'true':
        service.sms.send_msg(
            body=config.NEW_CUSTOMER_MESSAGE,
            to=data_dict["phone_number"])

    return jsonpickle.encode({
        "result": 0, "uuid": customer[CFields.UUID]},
        unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['GET'])
def customer_get(uuid):
    customer = Model.load_from_db(Customer, uuid)

    if customer is None:
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    return jsonpickle.encode({
        "result": 0, "customer": customer.get_data()},
        unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['PUT'])
def customer_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))
    customer = Model.load_from_db(Customer, uuid)

    if customer is None:
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer.update(data)

    # Save the customer to db
    if not customer.save():
        return common.error_to_json(Erros.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0}, unpicklable=False)

@app.route('/core/delegator', methods=['POST'])
def delegator_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    if not Delegator.MANDATORY_KEYS <= set(data):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    delegator = Delegator.create_new(data)

    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_ALREADY_EXISTS)

    if not delegator.is_unique():
        return common.error_to_json(Errors.DELEGATOR_ALREADY_EXISTS)

    if not delegator.create():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0, "uuid": delegator[DFields.UUID]}, unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['GET'])
def delegator_get(uuid):
    delegator = Model.load_from_db(Delegator, uuid)
    
    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    return jsonpickle.encode({
        "result": 0, "delegator": delegator.get_data()},
        unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['PUT'])
def delegator_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))
    delegator = Model.load_from_db(Delegator, uuid)

    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    delegator.update(data)
    
    if not delegator.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0, "delegator": delegator.get_data()})

@app.route('/core/delegator', methods=['GET'])
def delegator_list():
    query = models.delegators.scan()

    return jsonpickle.encode({
        "result": 0, "delegators": [delegator._data for delegator in query]},
        unpicklable=False)

@app.route('/core/send_message/<transaction_uuid>', methods=['POST'])
def send_message(transaction_uuid):
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not set(["from_customer", "content", "platform_type"]) <= set(data_dict.keys()):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    if not models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = models.transactions.get_item(uuid=transaction_uuid, consistent=True)

    message = Message(
        from_customer=data_dict["from_customer"],
        content=data_dict["content"],
        platform_type=data_dict["platform_type"])

    if transaction["messages"] is None:
        transaction["messages"] = []

    transaction["messages"].append(message.get_data())

    # Save data to the database
    transaction.partial_save()

    # If the message was sent by the delegator go ahead and send it to the customer
    # NOTE: will have to change as we introduce more platforms
    if not data_dict["from_customer"]:
        customer = models.customers.get_item(uuid=transaction["customer_uuid"], consistent=True)

        sms_chunks = [data_dict["content"][i : i + config.MAX_TWILIO_MSG_SIZE]
                for i in range(0, len(data_dict["content"]), config.MAX_TWILIO_MSG_SIZE)];

        for msg in sms_chunks:
            service.sms.send_msg(
                body=msg,
                to=customer["phone_number"])

    return jsonpickle.encode({
            "result": 0,
            "timestamp": message.timestamp
        }, unpicklable=False)

@app.route('/core/get_messages/<transaction_uuid>', methods=['GET'])
def get_messages(transaction_uuid):
    if not models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = models.transactions.get_item(uuid=transaction_uuid, consistent=True)

    to_return = {"result": 0}

    if transaction["messages"] is not None:
        to_return.update({"messages": [message for message in transaction["messages"]]})
    else:
        to_return.update({"messages": None})

    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/core/transaction', methods=['POST'])
def create_transaction():
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not set(["customer_uuid"]) <= set(data_dict.keys()):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    if not models.customers.has_item(uuid=data_dict["customer_uuid"], consistent=True):
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = models.customers.get_item(uuid=data_dict["customer_uuid"], consistent=True)

    # NOTE: client can only make transactions in the started state
    transaction = Transaction(
            customer_uuid=data_dict["customer_uuid"],
            status=TransactionStates.STARTED)
    transaction.payment_url = gator.payment.create_url(transaction.uuid)

    # Add the transaction to the transaction table
    models.transactions.put_item(data=transaction.get_data())

    # Add the transaction uuid to the customer
    if customer["active_transaction_uuids"] is None:
        customer["active_transaction_uuids"] = []

    customer["active_transaction_uuids"].append(transaction.uuid)
    customer.partial_save()

    # Send a text to all of the delegators
    for delegator in models.delegators.scan():
         service.sms.send_msg(
            body="ALERT: New transaction from %s" % customer["phone_number"],
            to=delegator["phone_number"])

    return jsonpickle.encode({"result": 0, "uuid": transaction.uuid}, unpicklable=False)

# TODO: write a test for PUT
# TODO: This is in need of some good-ole refractoring. Too much is going on in one method
@app.route('/core/transaction/<uuid>', methods=['GET', 'PUT'])
def transaction(uuid):
    if not models.transactions.has_item(uuid=uuid, consistent=True):
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    if request.method == 'PUT':
        data_dict = jsonpickle.decode(request.data.decode("utf-8"))

        # NOTE: do not allow both data fields to be changed in one operation
        # b/c it takes more logic to do that
        if not set(data_dict.keys()) < set(["delegator_uuid", "status", "receipt"]):
            return common.error_to_json(Errors.INVALID_DATA_PRESENT)

        transaction = models.transactions.get_item(uuid=uuid, consistent=True)

        # Update the state of associated delegator objects
        if "delegator_uuid" in data_dict:

            if "delegator_uuid" in transaction:
                old_delegator = models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)
                if transaction["status"] in TransactionStates.ACTIVE_TRANSACTION_STATES:
                    old_delegator["active_transaction_uuids"].remove(transaction["uuid"])
                else:
                    old_delegator["inactive_transaction_uuids"].remove(transaction["uuid"])
                old_delegator.partial_save()

            new_delegator = models.delegators.get_item(uuid=data_dict["delegator_uuid"], consistent=True)
            if transaction["status"] in TransactionStates.ACTIVE_TRANSACTION_STATES:
                if "active_transaction_uuids" not in new_delegator:
                    new_delegator["active_transaction_uuids"] = []
                new_delegator["active_transaction_uuids"].append(transaction["uuid"])
            else:
                if "inactive_transaction_uuids" not in new_delegator:
                    new_delegator["inactive_transaction_uuids"] = []
                new_delegator["inactive_transaction_uuids"].append(transaction["uuid"])
            new_delegator.partial_save()

        # Change the state
        if "status" in data_dict:
            old_status_is_active = transaction["status"] in TransactionStates.ACTIVE_TRANSACTION_STATES
            new_status_is_active = data_dict["status"] in TransactionStates.ACTIVE_TRANSACTION_STATES

            if old_status_is_active != new_status_is_active and "customer_uuid" in transaction:
                customer = models.customers.get_item(uuid=transaction["customer_uuid"], consistent=True)
                if old_status_is_active:
                    if "inactive_transaction_uuids" not in customer:
                        customer["inactive_transaction_uuids"] = []
                    customer["active_transaction_uuids"].remove(transaction["uuid"])
                    customer["inactive_transaction_uuids"].append(transaction["uuid"])
                else:
                    if "active_transaction_uuids" not in customer:
                        customer["active_transaction_uuids"] = []
                    customer["inactive_transaction_uuids"].remove(transaction["uuid"])
                    customer["active_transaction_uuids"].append(transaction["uuid"])
                customer.partial_save()

            if old_status_is_active != new_status_is_active and "delegator_uuid" in transaction:
                cur_delegator = models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)
                if old_status_is_active:
                    if "inactive_transaction_uuids" not in cur_delegator:
                        cur_delegator["inactive_transaction_uuids"] = []
                    cur_delegator["active_transaction_uuids"].remove(transaction["uuid"])
                    cur_delegator["inactive_transaction_uuids"].append(transaction["uuid"])
                else:
                    if "active_transaction_uuids" not in cur_delegator:
                        cur_delegator["active_transaction_uuids"] = []
                    cur_delegator["inactive_transaction_uuids"].remove(transaction["uuid"])
                    cur_delegator["active_transaction_uuids"].append(transaction["uuid"])
                cur_delegator.partial_save()

        if "receipt" in data_dict and "receipt" in transaction and "stripe_charge_id" in transaction["receipt"]:
            return common.error_to_json(Errors.TRANSACTION_ALREADY_PAID)

        # Update the transaction itself
        transaction._data.update(data_dict)

        # Save changes to the database
        transaction.partial_save()

        return jsonpickle.encode({"result": 0}, unpicklable=False)
    elif request.method == 'GET':
        transaction = models.transactions.get_item(uuid=uuid, consistent=True)

        to_return = {"result": 0, "transaction": transaction._data}
        return jsonpickle.encode(to_return, unpicklable=False)

@app.route("/core/assign_transaction/<delegator_uuid>", methods=["GET"])
def assign_transaction(delegator_uuid):
    if not models.delegators.has_item(uuid=delegator_uuid, consistent=True):
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    if models.transactions.query_count(index="status-index", status__eq=TransactionStates.STARTED) == 0:
        return common.error_to_json(Errors.NO_TRANSACTIONS_AVAILABLE)

    # Update the transaction
    transaction = models.transactions.query_2(index="status-index", status__eq=TransactionStates.STARTED).next()
    transaction["delegator_uuid"] = delegator_uuid
    transaction["status"] = TransactionStates.HELPED

    transaction.partial_save()

    # Update the delegator
    delegator = models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)

    if delegator.get("active_transaction_uuids") is None:
        delegator["active_transaction_uuids"] = []

    delegator["active_transaction_uuids"].append(transaction["uuid"])
    delegator.partial_save()
    
    return jsonpickle.encode({"result": 0, "transaction_uuid": transaction["uuid"]}, unpicklable=False)
