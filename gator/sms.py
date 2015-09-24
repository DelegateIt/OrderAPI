from flask import request

import gator.models
import gator.common

from gator import app

import jsonpickle

from twilio.rest import TwilioRestClient

ACCOUNT_SID = "ACb5440a719947d5edf7d760155a39a768"
AUTH_TOKEN = "dd9b4240a96556da1abb1e49646c73f3"

@app.route("/sms/handle_sms", methods=["POST"])
def handle_sms():
    print request.values
    return ""
