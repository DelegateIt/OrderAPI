from flask import request

import jsonpickle
import logging
import boto

import gator.config as config
import gator.core.service as service
import gator.core.models as models
import gator.core.common as common
import gator.core.push_endpoints as push_endpoints
import gator.logic.transactions as transactions

from gator.flask import app
from gator.core.models import Model, Customer, Delegator, Transaction, Message,\
                              CFields, DFields, TFields, MFields
from gator.core.common import Errors, TransactionStates, GatorException, Platforms,\
                              validate_phonenumber, validate_email
from gator.core.auth import authenticate, Permission, validate_permission,\
                            validate_fb_token, UuidType, login_facebook, validate_token

@app.after_request
def after_request(response):
    # TODO - Important Security - replace '*' with name of the server hosting the delegator web client
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    if request.method == 'OPTIONS':
        response.headers.add('Cache-Control', 'max-age=3153600')
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
            is_api_operational = service.sms.is_connected()
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

def login(uuid_type, data):
    if not set(["fbuser_id", "fbuser_token"]) <= set(data.keys()):
        raise GatorException(Errors.DATA_NOT_PRESENT)

    return login_facebook(data["fbuser_token"], data["fbuser_id"], uuid_type)

@app.route('/core/login/customer', methods=["POST"])
def customer_login():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    (uuid, token) = login(UuidType.CUSTOMER, data)
    customer = Model.load_from_db(Customer, uuid)

    # Create a push endpoint for the given device
    if "device_id" in data:
        push_endpoints.create_push_endpoint(customer, data["device_id"])

    return jsonpickle.encode({
        "result": 0, "customer": customer.get_data(), "token": token},
        unpicklable=False)

@app.route('/core/login/delegator', methods=["POST"])
def delegator_login():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    (uuid, token) = login(UuidType.DELEGATOR, data)
    delegator = Model.load_from_db(Delegator, uuid)
    return jsonpickle.encode({
        "result": 0, "delegator": delegator.get_data(), "token": token},
        unpicklable=False)

@app.route('/core/customer', methods=['POST'])
def customer_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    required = set([
        CFields.FIRST_NAME,
        CFields.LAST_NAME,
        CFields.FBUSER_ID,
        "fbuser_token"
    ])

    if CFields.PHONE_NUMBER in data:
        validate_phonenumber(data[CFields.PHONE_NUMBER])
    if CFields.EMAIL in data:
        validate_email(data[CFields.EMAIL])

    if not required <= set(data.keys()):
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
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

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
        "result": 0, "customer": customer.get_data(
            version=request.args.get("customer_version"))},
        unpicklable=False)

@app.route('/core/customer/<uuid>', methods=['PUT'])
@authenticate([Permission.CUSTOMER_OWNER])
def customer_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))
    customer = Model.load_from_db(Customer, uuid)

    if customer is None:
        return common.error_to_json(Errors.CUSTOMER_DOES_NOT_EXIST)

    if CFields.PHONE_NUMBER in data:
        validate_phonenumber(data[CFields.PHONE_NUMBER])
    if CFields.EMAIL in data:
        validate_email(data[CFields.EMAIL])

    if "fbuser_id" in data or "fbuser_token" in data:
        validate_fb_token(data["fbuser_token"], data["fbuser_id"])
        del data["fbuser_token"]

    customer.update(data)

    # Save the customer to db
    if not customer.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0}, unpicklable=False)

@app.route('/core/delegator', methods=['POST'])
def delegator_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    if not Delegator.MANDATORY_KEYS <= set(data):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    if DFields.PHONE_NUMBER in data:
        validate_phonenumber(data[DFields.PHONE_NUMBER])
    if DFields.EMAIL in data:
        validate_email(data[DFields.EMAIL])

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
        "result": 0, "delegator": delegator.get_data(
            version=request.args.get("delegator_version"))},
        unpicklable=False)

@app.route('/core/delegator/<uuid>', methods=['PUT'])
@authenticate([Permission.DELEGATOR_OWNER])
def delegator_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))
    delegator = Model.load_from_db(Delegator, uuid)

    if delegator is None:
        return common.error_to_json(Errors.DELEGATOR_DOES_NOT_EXIST)

    if DFields.PHONE_NUMBER in data:
        validate_phonenumber(data[DFields.PHONE_NUMBER])
    if DFields.EMAIL in data:
        validate_email(data[DFields.EMAIL])

    if "fbuser_id" in data or "fbuser_token" in data:
        validate_fb_token(data["fbuser_token"], data["fbuser_id"])
        del data["fbuser_token"]

    delegator.update(data)

    if not delegator.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({"result": 0}, unpicklable=False)

@app.route('/core/delegator', methods=['GET'])
def delegator_list():
    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.ALL_DELEGATORS])

    query = common.convert_query(Delegator, models.delegators.scan())

    return jsonpickle.encode({
        "result": 0, "delegators": [delegator.get_data() for delegator in query]},
        unpicklable=False)

@app.route('/core/send_message/<transaction_uuid>', methods=['POST'])
def send_message(transaction_uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))

    if not set([MFields.FROM_CUSTOMER, MFields.CONTENT, MFields.MTYPE]) <= set(data.keys()):
        return common.error_to_json(Errors.DATA_NOT_PRESENT)

    transaction = Model.load_from_db(Transaction, transaction_uuid)

    if transaction is None:
        return common.error_to_json(Errors.TRANSACTION_DOES_NOT_EXIST)

    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.CUSTOMER_OWNER, Permission.ALL_DELEGATORS], transaction["customer_uuid"])

    message = transactions.send_message(transaction, data[MFields.CONTENT],
            data[MFields.FROM_CUSTOMER], data[MFields.MTYPE])

    return jsonpickle.encode({
            "result": 0, "timestamp": message.get_timestamp()},
            unpicklable=False)

@app.route('/core/transaction', methods=['POST'])
def transaction_post():
    data = jsonpickle.decode(request.data.decode("utf-8"))

    # Authenticate the request
    token = request.args.get("token", "")
    validate_permission(validate_token(token), [Permission.CUSTOMER_OWNER], data["customer_uuid"])

    transaction = transactions.create_transaction(data)

    return jsonpickle.encode({
        "result": 0, "uuid": transaction[TFields.UUID]},
        unpicklable=False)
@app.route('/core/transaction', methods=['GET'])
def transaction_get_all():
    #TODO this really needs to be authenticated

    try:
        data = jsonpickle.decode(request.data.decode("utf-8"))
    except ValueError:
        data = request.args

    if TFields.CUSTOMER_UUID in data:
        query = models.transactions.query_2(
                customer_uuid__eq=data["customer_uuid"],
                consistent=True)
    elif TFields.DELEGATOR_UUID in data:
        query = models.transactions.query_2(
                delegator_uuid__eq=data["delegator_uuid"],
                index="delegator_uuid-index")
    else:
        raise GatorException(Errors.DATA_NOT_PRESENT)

    query = [Transaction(q).get_data() for q in query]
    return jsonpickle.encode({
        "result": 0,
        "transactions": query},
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
        "result": 0, "transaction": transaction.get_data(
            version=request.args.get("transaction_version"))},
        unpicklable=False)

@app.route('/core/transaction/<uuid>', methods=['PUT'])
@authenticate([])
def transaction_put(uuid):
    data = jsonpickle.decode(request.data.decode("utf-8"))

    #TODO verify identity has permission to update this resource
    transactions.update_transaction(uuid, data)

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
    transaction_data = Transaction(models.transactions.query_2(
        index="status-index",
        status__eq=TransactionStates.STARTED).next()).get_data()

    transaction = Model.load_from_db(Transaction, transaction_data["uuid"])
    transaction[TFields.DELEGATOR_UUID] = delegator_uuid
    transaction[TFields.STATUS] = TransactionStates.HELPED

    if not transaction.save():
        return common.error_to_json(Errors.CONSISTENCY_ERROR)

    return jsonpickle.encode({
        "result": 0, "transaction_uuid": transaction[TFields.UUID]},
        unpicklable=False)

@app.route("/core/quickorders", methods=["GET"])
def get_quickorders():
    return jsonpickle.encode({
        "result": 0,
        "quickorders": [
            {
                    "name": "airplane",
                    "order_text": "buy me an airplane",
                    "image": "http://delegateit-quickorders.s3-website-us-west-2.amazonaws.com/airplane.jpg"
            },
            {
                    "name": "coffee",
                    "order_text": "buy me a coffee",
                    "image": "http://delegateit-quickorders.s3-website-us-west-2.amazonaws.com/coffee.jpg"
            },
            {
                    "name": "concert",
                    "order_text": "buy me a concert ticket",
                    "image": "http://delegateit-quickorders.s3-website-us-west-2.amazonaws.com/concert.jpg"
            },
            {
                    "name": "pizza",
                    "order_text": "buy me a pizza",
                    "image": "http://delegateit-quickorders.s3-website-us-west-2.amazonaws.com/pizza.jpg"
            },
            {
                    "name": "rentals",
                    "order_text": "buy me some'm dem rentals, bitch",
                    "image": "http://delegateit-quickorders.s3-website-us-west-2.amazonaws.com/rental.jpg"
            },
            {
                    "name": "toilet paper",
                    "order_text": "buy me a toilet paper",
                    "image": "http://delegateit-quickorders.s3-website-us-west-2.amazonaws.com/toilet-paper.jpg"
            },
        ]
    })

@app.route("/core/sendgreeting", methods=["POST"])
def send_greeting():
    data = jsonpickle.decode(request.data.decode("utf-8"))
    if "phone_number" not in data.keys():
        return common.error_to_json(Errors.DATA_NOT_PRESENT)
    service.sms.send_msg(body=config.NEW_CUSTOMER_MESSAGE, to=data["phone_number"])
    return jsonpickle.encode({"result": 0})

@app.errorhandler(BaseException)
def handle_exception(e):
    if issubclass(type(e), GatorException):
        resp = {
            "result": e.error_type.returncode,
            "error_message": e.message,
            "type": type(e).__name__
        }
        if e.data is not None:
            resp["data"] = e.data
        return (jsonpickle.encode(resp), 400)
    else:
        logging.exception(e)
        return common.error_to_json(Errors.UNCAUGHT_EXCEPTION), 500
