from flask import request

import jsonpickle
import logging
import boto

import gator.service as service
import gator.models as models
import gator.common as common
import gator.config as config
import gator.payment as payment
import gator.business_logic as bl

from gator.flask import app
from gator.models import Model, Customer, Delegator, Transaction, Message
from gator.models import CFields, DFields, TFields, MFields
from gator.common import Errors, TransactionStates, GatorException, Platforms
from gator.auth import authenticate, Permission, validate_permission,\
                       validate_fb_token, UuidType, login_facebook, validate_token

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
    # Check at most once per hour
    check_overdue = common.get_current_timestamp() - last_status_check > 10**6 * 60 * 60
    if not is_api_operational or check_overdue:
        last_status_check = common.get_current_timestamp()
        try:
            models.customers.describe()
            accounts = service.sms.twilio.accounts.list()
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
    data = jsonpickle.decode(request.data.decode("utf-8"))
    if not set(["fbuser_id", "fbuser_token"]) <= set(data.keys()):
        raise GatorException(Errors.DATA_NOT_PRESENT)
    return login_facebook(data["fbuser_token"], data["fbuser_id"], uuid_type)

@app.route('/core/login/customer', methods=["POST"])
def customer_login():
    (uuid, token) = login(UuidType.CUSTOMER)
    customer = Model.load_from_db(Customer, uuid)
    return jsonpickle.encode({"result": 0, "customer": customer.get_data(), "token": token})

@app.route('/core/login/delegator', methods=["POST"])
def delegator_login():
    (uuid, token) = login(UuidType.DELEGATOR)
    delegator = Model.load_from_db(Delegator, uuid)
    return jsonpickle.encode({"result": 0, "delegator": delegator.get_data(), "token": token})

@app.route('/core/customer', methods=['POST'])
def customer_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    if not Customer.MANDATORY_KEYS <= set(data.keys()):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    # Authenticate the request
    if "fbuser_id" in data:
        validate_fb_token(data.get("fbuser_token"), data["fbuser_id"])
        del data["fbuser_token"]

    customer = Customer.create_new(data)

    if not customer.is_valid():
        return common.error_to_json(Errors.CUSTOMER_ALREADY_EXISTS)

    # Save the customer to db
    if not customer.create():
        return common.error_to_json(Erros.CONSISTENCY_ERROR)

    # Send a text to the user if they signed up from the LandingPage
    if request.args.get('sendtext', 'false') == 'true':
        service.sms.send_msg(
            body=config.NEW_CUSTOMER_MESSAGE,
            to=data[CFields.PHONE_NUMBER])

    return jsonpickle.encode({
        "result": 0, "uuid": customer[CFields.UUID]},
        unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['GET'])
@authenticate([Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS])
def customer(uuid):
    customer = Model.load_from_db(Customer, uuid)
    if customer is None:
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    return jsonpickle.encode({
        "result": 0, "customer": customer.get_data()},
        unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['PUT'])
@authenticate([Permission.CUSTOMER_OWNER])
def customer_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))
    customer = Model.load_from_db(Customer, uuid)

    if customer is None:
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    if "fbuser_id" in data or "fbuser_token" in data:
        validate_fb_token(data["fbuser_token"], data["fbuser_id"])
        del data["fbuser_token"]

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

    # Authenticate the request
    validate_fb_token(data.get("fbuser_token"), data["fbuser_id"])
    del data["fbuser_token"]

    delegator = Delegator.create_new(data)

    if not delegator.is_valid():
        return common.error_to_json(Errors.DELEGATOR_ALREADY_EXISTS)

    if not delegator.create():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0, "uuid": delegator[DFields.UUID]}, unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['GET'])
@authenticate([Permission.DELEGATOR_OWNER])
def delegator_get(uuid):
    delegator = Model.load_from_db(Delegator, uuid)

    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    return jsonpickle.encode({
        "result": 0, "delegator": delegator.get_data()},
        unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['PUT'])
@authenticate([Permission.DELEGATOR_OWNER])
def delegator_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))
    delegator = Model.load_from_db(Delegator, uuid)

    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    if "fbuser_id" in data or "fbuser_token" in data:
        validate_fb_token(data["fbuser_token"], data["fbuser_id"])
        del data["fbuser_token"]

    delegator.update(data)

    if not delegator.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0, "delegator": delegator.get_data()})

@app.route('/core/delegator', methods=['GET'])
def delegator_list():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.ALL_DELEGATORS])

    query = models.delegators.scan()

    return jsonpickle.encode({
        "result": 0, "delegators": [delegator._data for delegator in query]},
        unpicklable=False)

@app.route('/core/send_message/<transaction_uuid>', methods=['POST'])
def send_message(transaction_uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))

    if not set([MFields.FROM_CUSTOMER, MFields.CONTENT]) <= set(data.keys()):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    transaction = Model.load_from_db(Transaction, transaction_uuid)

    if transaction is None:
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], transaction["customer_uuid"])

    message = Message(
        from_customer=data[MFields.FROM_CUSTOMER],
        content=data[MFields.CONTENT])

    transaction.add_message(message)

    if not transaction.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    # If the message was sent by the delegator send an SMS to the customer
    # NOTE: will have to change as we introduce more platforms
    if not data[MFields.FROM_CUSTOMER] and transaction[TFields.CUSTOMER_PLATFORM_TYPE] == Platforms.SMS:
        customer = Model.load_from_db(Customer, transaction[TFields.CUSTOMER_UUID])
        service.sms.send_msg(body=data[MFields.CONTENT], to=customer[CFields.PHONE_NUMBER])

    return jsonpickle.encode({
            "result": 0, "timestamp": message.get_timestamp()},
            unpicklable=False)

@app.route('/core/transaction', methods=['POST'])
def transaction_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.CUSTOMER_OWNER], data["customer_uuid"])

    success, transaction, error = bl.create_transaction(data)

    if not success:
        return common.error_to_json(error)

    # Send a text to all of the delegators
    for delegator in models.delegators.scan():
         service.sms.send_msg(
            body="ALERT: New transaction from %s" % delegator["phone_number"],
            to=delegator[DFields.PHONE_NUMBER])

    return jsonpickle.encode({
        "result": 0, "uuid": transaction[TFields.UUID]},
        unpicklable=False)

@app.route('/core/transaction/<uuid>', methods=['GET'])
def transaction_get(uuid):
    transaction = Model.load_from_db(Transaction, uuid)

    if transaction is None:
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], transaction["customer_uuid"])

    return jsonpickle.encode({
        "result": 0, "transaction": transaction.get_data()},
        unpicklable=False)

@app.route('/core/transaction/<uuid>', methods=['PUT'])
@authenticate([])
def transaction_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))

    #TODO verify identity has permission to update this resource
    success, error = bl.update_transaction(uuid, data)

    if not success:
        return common.error_to_json(error)

    return jsonpickle.encode({"result": 0}, unpicklable=False)

@app.route("/core/assign_transaction/<delegator_uuid>", methods=["GET"])
@authenticate([Permission.DELEGATOR_OWNER])
def assign_transaction(delegator_uuid):
    delegator = Model.load_from_db(Delegator, delegator_uuid)
    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    #TODO the initial query count can be optimized out
    if models.transactions.query_count(index="status-index", status__eq=TransactionStates.STARTED, limit=1) == 0:
        return common.error_to_json(Errors.NO_TRANSACTIONS_AVAILABLE)

    # Update the transaction
    transaction_data = models.transactions.query_2(
        index="status-index",
        status__eq=TransactionStates.STARTED).next()._data

    transaction = Model.load_from_db(Transaction, transaction_data["uuid"])
    transaction[TFields.DELEGATOR_UUID] = delegator_uuid
    transaction[TFields.STATUS] = TransactionStates.HELPED

    # Update the delegator
    delegator.add_transaction(transaction)

    if not transaction.save() or not delegator.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({
        "result": 0, "transaction_uuid": transaction[TFields.UUID]},
        unpicklable=False)

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
        return common.error_to_json(Errors.UNCAUGHT_EXCEPTION), 500
