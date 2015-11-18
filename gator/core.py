from flask import request

import jsonpickle
import logging
import boto

import gator.service
import gator.models
import gator.common

from gator.flask import app
from gator.models import Customer, Message, Delegator, Transaction
from gator.common import Errors, TransactionStates, GatorException
from gator.auth import authenticate, validate_permission, Permission, login_facebook, UuidType

MAX_TWILIO_MSG_SIZE = 1600

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

last_status_check = 0
is_api_operational = False
@app.route('/health', methods=["GET"])
def get_health():
    global last_status_check, is_api_operational
    #check at most once per hour
    check_overdue = gator.common.get_current_timestamp() - last_status_check > 10**6 * 60 * 60
    if not is_api_operational or check_overdue:
        last_status_check = gator.common.get_current_timestamp()
        try:
            gator.models.customers.describe()
            accounts = gator.service.sms.twilio.accounts.list()
            is_api_operational = len(accounts) > 0
        except Exception as e:
            logging.exception(e)
            is_api_operational = False
    status = is_api_operational
    payload = {
        "status": "good" if status else "bad",
        "result": 0
    }
    http_code = 200 if status else 500
    return jsonpickle.encode(payload), http_code

def login(uuid_type):
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))
    if not set(["fbuser_id", "fbuser_token"]) <= set(data_dict.keys()):
        raise GatorException(Errors.DATA_NOT_PRESENT)
    return login_facebook(data_dict["fbuser_token"], data_dict["fbuser_id"], uuid_type)

@app.route('/core/login/customer', methods=["POST"])
def customer_login():
    (uuid, token) = login(UuidType.CUSTOMER)
    customer = gator.models.customers.get_item(uuid=uuid, consistent=True)
    return jsonpickle.encode({"result": 0, "customer": customer._data, "token": token})

@app.route('/core/login/delegator', methods=["POST"])
def delegator_login():
    (uuid, token) = login(UuidType.DELEGATOR)
    delegator = gator.models.delegators.get_item(uuid=uuid, consistent=True)
    return jsonpickle.encode({"result": 0, "delegator": delegator._data, "token": token})

@app.route('/core/customer', methods=['POST'])
def create_customer():
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not set(["phone_number"]) <= set(data_dict.keys()):
        return gator.common.error_to_json(Errors.DATA_NOT_PRESENT)

    if "fbuser_id" in data_dict:
        gator.auth.validate_fb_token(data_dict.get("fbuser_token"), data_dict["fbuser_id"])
    customer = Customer.create_from_dict(data_dict)

    if not customer.is_unique():
        return gator.common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

    gator.models.customers.put_item(data=customer.get_data())

    if request.args.get('sendtext', 'false') == 'true':
        gator.service.sms.send_msg(
            body="Welcome to DelegateIt! Text us whatever you want and we will get it to you.",
            to=data_dict["phone_number"])

    return jsonpickle.encode({"result": 0, "uuid": customer.uuid}, unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['GET'])
@authenticate
def customer(uuid, identity):
    validate_permission(identity, [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], uuid)
    if not gator.models.customers.has_item(uuid=uuid, consistent=True):
        return gator.common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = gator.models.customers.get_item(uuid=uuid, consistent=True)

    to_return = {"result": 0}
    to_return.update(customer._data)
    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['PUT'])
@authenticate
def update_customer(uuid, identity):
    validate_permission(identity, [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], uuid)
    try:
        customer = gator.models.customers.get_item(uuid=uuid, consistent=True)
    except boto.dynamodb2.exceptions.ItemNotFound:
        return gator.common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)
    req_data = jsonpickle.decode(request.data.decode("utf-8"))
    if "fbuser_id" in req_data or "fbuser_token" in req_data:
        gator.auth.validate_fb_token(req_data["fbuser_token"], req_data["fbuser_id"])
        del req_data["fbuser_token"]
    customer._data.update(req_data)
    customer.partial_save()

    to_return = {"result": 0, "customer": customer._data}
    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['PUT'])
@authenticate
def update_delegator(uuid, identity):
    validate_permission(identity, [Permission.DELEGATOR_OWNER], uuid)
    try:
        delegator = gator.models.delegators.get_item(uuid=uuid, consistent=True)
    except boto.dynamodb2.exceptions.ItemNotFound:
        return gator.common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)
    req_data = jsonpickle.decode(request.data.decode("utf-8"))
    delegator._data.update(req_data)
    delegator.partial_save()

    to_return = {"result": 0, "delegator": delegator._data}
    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/core/delegator', methods=['POST'])
@authenticate
def create_delegator(identity):
    validate_permission(identity, [Permission.ADMIN])
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not set(["phone_number", "email", "first_name", "last_name",
            "fbuser_id", "fbuser_token"]) <= set(data_dict.keys()):
        return gator.common.error_to_json(Errors.DATA_NOT_PRESENT)

    gator.auth.validate_fb_token(data_dict.get("fbuser_token"), data_dict["fbuser_id"])

    delegator = Delegator(
            first_name=data_dict["first_name"],
            last_name=data_dict["last_name"],
            phone_number=data_dict["phone_number"],
            email=data_dict["email"],
            fbuser_id=data_dict["fbuser_id"])

    if not delegator.is_unique():
        return gator.common.error_to_json(Errors.DELEGATOR_ALREADY_EXISTS)

    gator.models.delegators.put_item(data=delegator.get_data())

    return jsonpickle.encode({"result": 0, "uuid": delegator.uuid}, unpicklable=False)

@app.route('/core/delegator', methods=['GET'])
@authenticate
def list_delegators(identity):
    query = gator.models.delegators.scan()
    return jsonpickle.encode({
        "result": 0,
        "delegators": [delegator._data for delegator in query]},
        unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['GET'])
@authenticate
def delegator(uuid, identity):
    validate_permission(identity, [Permission.DELEGATOR_OWNER], uuid)
    if not gator.models.delegators.has_item(uuid=uuid, consistent=True):
        return gator.common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    delegator = gator.models.delegators.get_item(uuid=uuid, consistent=True)

    to_return = {"result": 0}
    to_return.update(delegator._data)
    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/core/send_message/<transaction_uuid>', methods=['POST'])
@authenticate
def send_message(transaction_uuid, identity):
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not set(["from_customer", "content", "platform_type"]) <= set(data_dict.keys()):
        return gator.common.error_to_json(Errors.DATA_NOT_PRESENT)

    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return gator.common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)

    validate_permission(identity, [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], transaction["customer_uuid"])

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
        customer = gator.models.customers.get_item(uuid=transaction["customer_uuid"], consistent=True)

        sms_chunks = [data_dict["content"][i : i + MAX_TWILIO_MSG_SIZE]
                for i in range(0, len(data_dict["content"]), MAX_TWILIO_MSG_SIZE)];

        for msg in sms_chunks:
            gator.service.sms.send_msg(
                body=msg,
                to=customer["phone_number"])

    # Notify the delegator that there is a new message
    if not transaction["delegator_uuid"] is None and data_dict["from_customer"]:
        delegator = gator.models.delegators.get_item(uuid=transaction["delegator_Uuid"], consistent=True)

        gator.service.sms.send_msg(
                body="ALERT: new message from customer",
                to=delegator["phone_number"])
        
    return jsonpickle.encode({
            "result": 0,
            "timestamp": message.timestamp
        }, unpicklable=False)

#TODO this method is not used by any clients. Perhaps extermination?
@app.route('/core/get_messages/<transaction_uuid>', methods=['GET'])
@authenticate
def get_messages(transaction_uuid, identity):
    if not gator.models.transactions.has_item(uuid=transaction_uuid, consistent=True):
        return gator.common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    transaction = gator.models.transactions.get_item(uuid=transaction_uuid, consistent=True)

    validate_permission(identity, [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], transaction["customer_uuid"])

    to_return = {"result": 0}

    if transaction["messages"] is not None:
        to_return.update({"messages": [message for message in transaction["messages"]]})
    else:
        to_return.update({"messages": None})

    return jsonpickle.encode(to_return, unpicklable=False)

@app.route('/core/transaction', methods=['POST'])
@authenticate
def create_transaction(identity):
    data_dict = jsonpickle.decode(request.data.decode("utf-8"))

    if not set(["customer_uuid"]) <= set(data_dict.keys()):
        return gator.common.error_to_json(Errors.DATA_NOT_PRESENT)
    validate_permission(identity, [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], data_dict["customer_uuid"])

    if not gator.models.customers.has_item(uuid=data_dict["customer_uuid"], consistent=True):
        return gator.common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    customer = gator.models.customers.get_item(uuid=data_dict["customer_uuid"], consistent=True)

    # NOTE: client can only make transactions in the started state
    transaction = Transaction(
            customer_uuid=data_dict["customer_uuid"],
            status=TransactionStates.STARTED)
    transaction.payment_url = gator.payment.create_url(transaction.uuid)

    # Add the transaction to the transaction table
    gator.models.transactions.put_item(data=transaction.get_data())

    # Add the transaction uuid to the customer
    if customer["active_transaction_uuids"] is None:
        customer["active_transaction_uuids"] = []

    customer["active_transaction_uuids"].append(transaction.uuid)
    customer.partial_save()

    # Send a text to all of the delegators
    for delegator in gator.models.delegators.scan():
         gator.service.sms.send_msg(
            body="ALERT: New transaction from %s" % customer["phone_number"],
            to=delegator["phone_number"])

    return jsonpickle.encode({"result": 0, "uuid": transaction.uuid}, unpicklable=False)

# TODO: write a test for PUT
# TODO: This is in need of some good-ole refractoring. Too much is going on in one method
@app.route('/core/transaction/<uuid>', methods=['GET', 'PUT'])
@authenticate
def transaction(uuid, identity):
    if not gator.models.transactions.has_item(uuid=uuid, consistent=True):
        return gator.common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)
    transaction = gator.models.transactions.get_item(uuid=uuid, consistent=True)
    validate_permission(identity, [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], transaction["customer_uuid"])

    if request.method == 'PUT':
        data_dict = jsonpickle.decode(request.data.decode("utf-8"))

        # NOTE: do not allow both data fields to be changed in one operation
        # b/c it takes more logic to do that
        if not set(data_dict.keys()) < set(["delegator_uuid", "status", "receipt"]):
            return gator.common.error_to_json(Errors.INVALID_DATA_PRESENT)

        # Update the state of associated delegator objects
        if "delegator_uuid" in data_dict:

            if "delegator_uuid" in transaction:
                old_delegator = gator.models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)
                if transaction["status"] in TransactionStates.ACTIVE_TRANSACTION_STATES:
                    old_delegator["active_transaction_uuids"].remove(transaction["uuid"])
                else:
                    old_delegator["inactive_transaction_uuids"].remove(transaction["uuid"])
                old_delegator.partial_save()

            new_delegator = gator.models.delegators.get_item(uuid=data_dict["delegator_uuid"], consistent=True)
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
                customer = gator.models.customers.get_item(uuid=transaction["customer_uuid"], consistent=True)
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
                cur_delegator = gator.models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)
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
            return gator.common.error_to_json(Errors.TRANSACTION_ALREADY_PAID)

        # Update the transaction itself
        transaction._data.update(data_dict)

        # Save changes to the database
        transaction.partial_save()

        return jsonpickle.encode({"result": 0}, unpicklable=False)
    elif request.method == 'GET':
        to_return = {"result": 0, "transaction": transaction._data}
        return jsonpickle.encode(to_return, unpicklable=False)

@app.route("/core/assign_transaction/<delegator_uuid>", methods=["GET"])
@authenticate
def assign_transaction(delegator_uuid, identity):
    validate_permission(identity, [Permission.DELEGATOR_OWNER], delegator_uuid)
    if not gator.models.delegators.has_item(uuid=delegator_uuid, consistent=True):
        return gator.common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    if gator.models.transactions.query_count(index="status-index", status__eq=TransactionStates.STARTED) == 0:
        return gator.common.error_to_json(Errors.NO_TRANSACTIONS_AVAILABLE)

    # Update the transaction
    transaction = gator.models.transactions.query_2(index="status-index", status__eq=TransactionStates.STARTED).next()
    transaction["delegator_uuid"] = delegator_uuid
    transaction["status"] = TransactionStates.HELPED

    transaction.partial_save()

    # Update the delegator
    delegator = gator.models.delegators.get_item(uuid=transaction["delegator_uuid"], consistent=True)

    if delegator.get("active_transaction_uuids") is None:
        delegator["active_transaction_uuids"] = []

    delegator["active_transaction_uuids"].append(transaction["uuid"])
    delegator.partial_save()

    return jsonpickle.encode({"result": 0, "transaction_uuid": transaction["uuid"]}, unpicklable=False)

@app.errorhandler(BaseException)
def handle_exception(e):
    if issubclass(type(e), GatorException):
        return (jsonpickle.encode({
            "result": e.error_type.returncode,
            "error_message": e.message,
            "type": type(e).__name__
        }), 400)
    else:
        logging.exception(e)
        return gator.common.error_to_json(Errors.UNCAUGHT_EXCEPTION), 500
