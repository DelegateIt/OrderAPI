import flask

app = flask.Flask(__name__)
app.debug = True

import gator.rest_handler
import gator.payment
