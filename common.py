from enum import Enum

class Exceptions():
    CUSTOMER_DOES_NOT_EXIST  = "The specified phone number is not linked to a valid customer"
    DATA_NOT_PRESENT     = "The certain request could not be completed without valid data"
    UNSUPPORTED_PLATFORM = "The platform you specified is not supported"
