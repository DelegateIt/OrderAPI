from enum import Enum

class Exceptions():
    USER_DOES_NOT_EXIST  = "The specified phone number is not linked to a valid user"
    DATA_NOT_PRESENT     = "The certain request could not be completed without valid data"
    UNSUPPORTED_PLATFORM = "The platform you specified is not supported"
