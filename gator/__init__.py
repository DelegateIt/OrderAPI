import flask
from flask.ext.socketio import SocketIO

app = flask.Flask(__name__)
app.debug = True

socketio = SocketIO(app)

import gator.rest_handler
import gator.payment
import gator.streams
