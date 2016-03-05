import flask
import logging

app = flask.Flask(__name__)

logging.getLogger().setLevel(logging.INFO)

import gator.endpoints.core
import gator.endpoints.payment
import gator.endpoints.sms
import gator.endpoints.notify
import gator.endpoints.push
