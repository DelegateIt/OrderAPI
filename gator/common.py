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

def error_to_json(error):
    return jsonpickle.encode({
            "result": error.returncode,
            "error_message": error.err_message
        })

class GatorException(Exception):
    def __init__(self, error_type, message=None):
        self.message = error_type.err_message if message is None else message
        self.error_type = error_type
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
    ACTIVE_STATES = [STARTED, HELPED, PROPOSED]

class Platforms():
    SMS =     "sms"
    ANDROID = "android"
    IOS =     "ios"
    WEB =     "web"

    VALID_PLATFORMS = [SMS, ANDROID, IOS, WEB]

####################
# Helper Functions #
####################

def get_uuid():
    return str(uuid.uuid4().int >> 64)

def get_current_timestamp():
    return int(time.time() * 10**6)
