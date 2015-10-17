import flask
import logging

app = flask.Flask(__name__)
app.debug = True

logging.getLogger().setLevel(logging.INFO)

import gator.core
import gator.payment
import gator.sms
import gator.notify
