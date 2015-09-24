import flask
from flask.ext.socketio import SocketIO

app = flask.Flask(__name__)
app.debug = True

socketio = SocketIO(app)

import gator.core
import gator.payment
import gator.streams
import gator.sms
