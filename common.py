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
    CUSTOMER_DOES_NOT_EXIST    = ErrorType(0, "The specified uuid is not linked to a customer")
    DATA_NOT_PRESENT           = ErrorType(1, "The request could not be completed without the required data")
    CUSTOMER_ALREADY_EXISTS    = ErrorType(2, "The specified customer already exists")
    TRANSACTION_DOES_NOT_EXIST = ErrorType(3, "The specified transaction does not exist")
    DELEGATOR_ALREADY_EXISTS   = ErrorType(4, "The specified delegator already exists")
    DELEGATOR_DOES_NOT_EXIST   = ErrorType(5, "The specified uuid is not linked to a delegator")

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
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
