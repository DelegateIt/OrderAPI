import jsonpickle
import decimal

##########
# Errors #
##########

class ErrorType():
    def __init__(self, returncode, err_message):
        self.returncode  = returncode
        self.err_message = err_message

class Errors():
    # NOTE: do not change the returncode of these functions
    CUSTOMER_DOES_NOT_EXIST    = ErrorType(1, "The specified phone number is not linked to a valid customer")
    DATA_NOT_PRESENT           = ErrorType(2, "The request could not be completed without the required data")
    UNSUPPORTED_PLATFORM       = ErrorType(3, "The platform you specified is not supported")
    CUSTOMER_ALREADY_EXISTS    = ErrorType(4, "The specified customer already exists")
    TRANSACTION_DOES_NOT_EXIST = ErrorType(5, "The specified transaction does not exist")

def error_to_json(error):
    return jsonpickle.encode({
            "result": error.returncode,
            "error_message": error.err_message
        })

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

class TransactionStatus():
    STARTED   = "started"
    HELPED    = "helped"
    COMPLETED = "completed"
