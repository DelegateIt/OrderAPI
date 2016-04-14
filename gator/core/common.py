import re
import decimal
import uuid
import time

import jsonpickle

##########
# Errors #
##########

class ErrorType():
    def __init__(self, returncode, err_message):
        self.returncode  = returncode
        self.err_message = err_message

class Errors():
    # NOTE: do not change the return code of these variables
    DATA_NOT_PRESENT           = ErrorType(1, "The request was missing required data")
    CUSTOMER_ALREADY_EXISTS    = ErrorType(2, "The specified customer already exists")
    TRANSACTION_DOES_NOT_EXIST = ErrorType(3, "The specified transaction does not exist")
    DELEGATOR_ALREADY_EXISTS   = ErrorType(4, "The specified delegator already exists")
    DELEGATOR_DOES_NOT_EXIST   = ErrorType(5, "The specified uuid is not linked to a delegator")
    INVALID_DATA_PRESENT       = ErrorType(6, "The request contained inconsistent or superfluous data")
    TRANSACTION_ALREADY_PAID   = ErrorType(7, "The transaction has already been paid for and cannot be modified")
    NO_TRANSACTIONS_AVAILABLE  = ErrorType(8, "There are no unhelped transactions available")
    DELEGATOR_DOES_NOT_EXIST   = ErrorType(9, "The specified uuid is not linked to a delegator")
    CUSTOMER_DOES_NOT_EXIST    = ErrorType(10, "The specified uuid is not linked to a customer")
    UNCAUGHT_EXCEPTION         = ErrorType(11, "The server encountered an internel error")
    INVALID_TOKEN              = ErrorType(12, "The authentication token is not valid")
    INVALID_FACEBOOK_TOKEN     = ErrorType(13, "Facebook could not validate the token")
    PERMISSION_DENIED          = ErrorType(14, "You do not have the access rights for that resource")
    CONSISTENCY_ERROR          = ErrorType(15, "The request could not be completed due to a consistency issue")
    INVALID_PLATFORM           = ErrorType(16, "The specified platform is invalid")
    STRIPE_ERROR               = ErrorType(17, "Stripe encountered an internal error")
    RECEIPT_NOT_SAVED          = ErrorType(18, "The receipt for the transaction has not been saved")
    INVALID_MSG_TYPE           = ErrorType(19, "The specified message type is invalid")
    INVALID_EMAIL              = ErrorType(20, "The email address is invalid")
    INVALID_PHONE_NUMBER       = ErrorType(21, "The phone number is invalid")
    UNSUPORTED_VERSION         = ErrorType(22, "The specified version is no longer supported")
    STALE_API_VERSION          = ErrorType(23, "The API is not up to date with the latest version")
    SNS_FAILURE                = ErrorType(24, "Amazon SNS sent back an error")
    POSTMATES_ERROR            = ErrorType(25, "The Postmates API returned an error")


def error_to_json(error):
    return jsonpickle.encode({
            "result": error.returncode,
            "error_message": error.err_message
        })

class GatorException(Exception):
    def __init__(self, error_type, message=None, data=None):
        self.message = error_type.err_message if message is None else message
        self.error_type = error_type
        self.data = data
        Exception.__init__(self, self.message)

    def __str__(self):
        return type(self).__name__ + " - " + str(self.error_type.returncode) + " - " + self.message


############################
# Pickle/Unpickle Handlers #
############################

class BotoDecimalHandler(jsonpickle.handlers.BaseHandler):
    """
    Automatically convert Decimal types (returned by DynamoDB) to ints
    """
    def flatten(self, obj, data):
        data = int(obj)
        return data

jsonpickle.handlers.register(decimal.Decimal, BotoDecimalHandler)

################
# Transactions #
################

class TransactionStates():
    STARTED   = "started"
    HELPED    = "helped"
    PROPOSED  = "proposed"
    CONFIRMED = "confirmed"
    PENDING   = "pending"
    COMPLETED = "completed"

    VALID_STATES = [STARTED, HELPED, PROPOSED, CONFIRMED, PENDING, COMPLETED]
    ACTIVE_STATES = [STARTED, HELPED, PROPOSED, CONFIRMED, PENDING]

class Platforms():
    SMS =     "sms"
    ANDROID = "android"
    IOS =     "ios"
    WEB =     "web"

    VALID_PLATFORMS = [SMS, ANDROID, IOS, WEB]

##############
# Validators #
##############

EMAIL_REGEX = re.compile("^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile("^\+?[0-9]{11}$")

def validate_email(email):
    if EMAIL_REGEX.match(email) is None:
        raise GatorException(Errors.INVALID_EMAIL, data={"email": email})

def validate_phonenumber(phonenumber):
    if PHONE_REGEX.match(phonenumber) is None:
        raise GatorException(Errors.INVALID_PHONE_NUMBER, data={"phone": phonenumber})

####################
# Helper Functions #
####################

def get_uuid():
    return str(uuid.uuid4().int >> 64)

def get_current_timestamp():
    return int(time.time() * 10**6)

def convert_query(cls, query):
    for item in query:
        yield cls(item)

def get_customer_alias(customer):
    first_name = customer.get("first_name")
    last_name  = customer.get("last_name")
    name = "%s %s" % (first_name, last_name)

    return name if first_name is not None or last_name is not None \
            else customer.get("phone_number", "UNKNOWN")

########
# Misc #
########

class PostmatesAddress():
    VALID_KEYS = ['name', 'address', 'phone_number', 'business_name', 'notes']

    def __init__(self, name, address, phone_number, business_name='', notes=''):
        self.name = name
        self.address = address
        self.phone_number = phone_number
        self.business_name = business_name
        self.notes = notes

    def __getitem__(self, key):
        if key not in self.VALID_KEYS:
            raise KeyError('%s is not a valid key' % key)

        return self.__dict__.get(key)

    def get_data(self, is_pickup):
        prefix = 'pickup_' if is_pickup else 'dropoff_'
        return {prefix + key: self[key] for key in self.VALID_KEYS}
