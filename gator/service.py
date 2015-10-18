""" The service initializer

This file is responsible for intializing the appropriate service by determining
if the system is in test or production mode
"""

import os
import json
import logging
import urllib2

import stripe
from twilio.rest import TwilioRestClient
import boto.dynamodb2
from boto.dynamodb2.layer1 import DynamoDBConnection

# Global services. Initalized at bottom
sms = None
shorturl = None
dynamodb = None


#######################
# Service Definitions #
#######################

class SmsService(object):
    def send_msg(self, to, body, _from="+15123593557"):
        logging.info("TEST: Sent SMS to {} from {} with body: {}".format(to, _from, body))

class TwilioService(SmsService):
    def __init__(self, account_sid, auth_token):
        self.twilio = TwilioRestClient(account_sid, auth_token)

    def send_msg(self, to, body, from_="+15123593557"):
        self.twilio.messages.create(body=body, to=to, from_=from_)

class ShortUrlService(object):
    def shorten_url(self, long_url):
        logging.info("TEST: shortened url {}".format(long_url))
        return long_url

class GoogleUrlService(object):
    def __init__(self, key):
        self.api_url = 'https://www.googleapis.com/urlshortener/v1/url?key={}'.format(key)

    def shorten_url(self, long_url):
        data = json.dumps({'longUrl': long_url})
        req = urllib2.Request(self.api_url, data)
        req.add_header('Content-Type', 'application/json')
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError as e:
            logging.exception(e)
            return long_url
        else:
            return json.loads(response.read())["id"]

##########################
# Service Initialization #
##########################

_is_test_mode = True

def is_test_mode():
    return _is_test_mode

def _create_sms():
    if is_test_mode():
        return SmsService()
    else:
        return TwilioService("ACb5440a719947d5edf7d760155a39a768", "dd9b4240a96556da1abb1e49646c73f3")

def _create_dynamodb():
    if is_test_mode() or "DB_PORT" in os.environ:
        host = "localhost"
        port = 8040

        #if inside a docker container linked to the db container
        if "DB_PORT" in os.environ:
            host = os.environ["DB_PORT"][6:].split(":")[0]
            port = os.environ["DB_PORT"][6:].split(":")[1]

        return DynamoDBConnection(
            aws_access_key_id='foo',
            aws_secret_access_key='bar',
            host=host,
            port=port,
            is_secure=False)
    else:
        return boto.dynamodb2.connect_to_region(
                         "us-west-2",
                         aws_access_key_id="AKIAJPVNCRLPXP6HA3ZQ",
                         aws_secret_access_key="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")


def _create_urlshortener():
    if is_test_mode():
        return ShortUrlService()
    else:
        return GoogleUrlService("AIzaSyBr49DAB57RHciOXU2-bNaZl_kfolM3XFk")

def _setup_stripe():
    if is_test_mode():
        stripe.api_key = "sk_test_WYJIBAm8Ut2kMBI2G6qfEbAH"
    else:
        #TODO Replace with production key
        stripe.api_key = "sk_test_WYJIBAm8Ut2kMBI2G6qfEbAH"

sms = _create_sms()
dynamodb = _create_dynamodb()
shorturl = _create_urlshortener()
_setup_stripe()

