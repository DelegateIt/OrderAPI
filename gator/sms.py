import gator.models
import gator.common

from gator import app

@app.route("/sms/handle_sms")
def handle_sms(data):
    print data

    return '{"result": 0}'
