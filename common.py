import json

##########
# Errors #
##########

class ErrorType():
    def __init__(self, returncode, err_message):
        self.returncode  = returncode
        self.err_message = err_message

class Errors():
    # NOTE: do not change the returncode of these functions
    CUSTOMER_DOES_NOT_EXIST  = ErrorType(1, "The specified phone number is not linked to a valid customer")
    DATA_NOT_PRESENT         = ErrorType(2, "The request could not be completed without the required data")
    UNSUPPORTED_PLATFORM     = ErrorType(3, "The platform you specified is not supported")
    CUSTOMER_ALREADY_EXISTS  = ErrorType(4, "The specified customer already exists")

def error_to_json(error):
    return json.dumps({
            "result": error.returncode,
            "error_message": error.err_message
        })

################
# Transactions #
################

class TransactionStatus():
    STARTED   = 0
    HELPED    = 1
    COMPLETED = 2
