import json
import os

# This is just a template, the actual config is loaded from disk on startup,
# then overwrites the below data.
# Most config changes should occur in the json config file, NOT here.
store = {
    "api_host": {
        "name": "localhost",
        "bind_port": 8000,
        "recv_port": 8000,
    },
    "notifier_host": {
        "bind_port": 8060,
        "recv_port": 8060,
    },
    "dynamodb": {
        "region": "us-west-2",
        "access_key": None,
        "secret_key": None,
        "endpoint": {
            "hostname": "localhost",
            "port": 8040,
        },
    },
    "twilio": {
        "account_sid": None,
        "auth_token": None,
    },
    "google": {
        "api_key": None,
    },
    "stripe": {
        "secret_key": None,
        "public_key": None,
    },
    "mode": "test",
}

def load_from_disk(filepath):
    global store
    with open(filepath, "r") as f:
        store = json.loads(f.read())

def print_to_stdout():
    print(json.dumps(store, indent=4))

load_from_disk(os.environ["GATOR_CONFIG_PATH"])
