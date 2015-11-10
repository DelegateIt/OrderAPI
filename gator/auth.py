from gator.common import get_current_timestamp, Errors, GatorException, get_uuid
from gator.config import  store
from gator import models

from enum import Enum
import requests
import hashlib
import base64

class Permission(Enum):
    CUSTOMER_OWNER = 1
    DELEGATOR_OWNER = 2
    ALL_DELEGATORS = 3
    API_NOTIFY = 5
    API_SMS = 6
    ADMIN = 7

class UuidType(Enum):
    CUSTOMER = "customer"
    DELEGATOR = "delegator"
    API = "api"

def validate_fb_token(fbuser_token, fbuser_id):
    if not store["authentication"]["validate_facebook_tokens"]:
        return
    try:
        url = "https://graph.facebook.com/me?fields=id&access_token={}".format(fbuser_token)
        resp = requests.get(url, timeout=0.5)
        actual_id = json.loads(resp)["id"]
        if fbuser_id != actual_id:
            raise GatorException(Errors.INVALID_FACEBOOK_TOKEN)
    except requests.exceptions.RequestException as e:
        logging.exception(e)
        raise GatorException(Errors.INVALID_FACEBOOK_TOKEN)

def _hash(uuid, uuid_type, expires):
    data = uuid + ":" + uuid_type.value + ":" + str(expires) + ":" + store["authentication"]["secret"]
    return base64.b64encode(hashlib.sha256(data.encode("utf-8")).digest()).decode("utf-8")

def _create_token(uuid, uuid_type, expire_delta=24*60*60): # expires in one day
        expires = get_current_timestamp() // 10**6 + expire_delta
        data = uuid + ":" + uuid_type.value + ":" + str(expires)
        data_hash = _hash(uuid, uuid_type, expires)
        return base64.b64encode((data + ":" + data_hash).encode("utf-8")).decode("utf-8")

def _retreive_uuid(fbuser_id, uuid_type):
    if uuid_type == UuidType.CUSTOMER:
        query = models.customers.query_2(index="fbuser_id-index", fbuser_id__eq=fbuser_id)
        #query = models.customers.query_2(index="fbuser_id-index", attributes=("uuid",),
        #        limit=1, fbuser_id__eq=fbuser_id)
        query = [r["uuid"] for r in query]
        if len(query) == 0:
            raise GatorException(Errors.CUSTOMER_DOES_NOT_EXIST)
    elif uuid_type == UuidType.DELEGATOR:
        query = models.delegators.query_2(index="fbuser_id-index", attributes=("uuid",),
                limit=1, fbuser_id__eq=fbuser_id)
        query = [r["uuid"] for r in query]
        if len(query) == 0:
            raise GatorException(Errors.DELEGATOR_DOES_NOT_EXIST)
    else:
       raise GatorException(Errors.INVALID_DATA_PRESENT)
    return query[0]

def _validate_api_permission(uuid, permission_list):
    api_keys = store["authentication"]["api_keys"]
    key = None
    for k in api_keys.values():
        if k["id"] == uuid:
            key = k
            break
    if key is None:
        raise GatorException(Errors.INVALID_TOKEN)
    for p in permission_list:
        if p.name in key["permissions"]:
            return
    #import logging
    #logging.warning("p_list: " + str(permission_list) + " accept: " + str(key["permissions"]))
    raise GatorException(Errors.PERMISSION_DENIED)

def login_facebook(fbuser_token, fbuser_id, uuid_type):
    validate_fb_token(fbuser_token, fbuser_id)
    uuid = _retreive_uuid(fbuser_id, uuid_type)
    return (uuid, _create_token(uuid, uuid_type))

def validate_permission(identity, permission_list, resource_uuid=None):
    (uuid, uuid_type) = identity
    if uuid_type == UuidType.API:
        _validate_api_permission(uuid, permission_list)
    else:
        for p in permission_list:
            if _permission_checker[p](uuid, uuid_type, resource_uuid):
                return
        raise GatorException(Errors.PERMISSION_DENIED)


def validate(token, permission_list, resource_uuid=None):
    (uuid, uuid_type) = validate_token(token)
    validate_permission(uuid, uuid_type, permission_list, resource_uuid)
    return (uuid, uuid_type)

def validate_token(token):
    parts = base64.b64decode(token).decode("utf-8").split(":")
    if len(parts) != 4 or int(parts[2]) < get_current_timestamp() // 10**6:
        raise GatorException(Errors.INVALID_TOKEN)
    uuid_type = UuidType(parts[1])
    uuid = parts[0]
    if uuid_type == UuidType.API:
        keys = store["authentication"]["api_keys"]
        if token not in keys:
            raise GatorException(Errors.INVALID_TOKEN)
    else:
        hashed = _hash(uuid, uuid_type, parts[2])
        if hashed != parts[3]:
            raise GatorException(Errors.INVALID_TOKEN)
    return (uuid, uuid_type)

def authenticate(f):
    from flask import request
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get("token", "")
        identity = validate_token(token)
        return f(*args, identity=identity, **kwargs)
    return decorated

#######################
# Permission checkers #
#######################

def _check_customer_owner(uuid, uuid_type, resource_uuid):
    return uuid == resource_uuid and uuid_type == UuidType.CUSTOMER

def _check_delegator_owner(uuid, uuid_type, resource_uuid):
    return uuid == resource_uuid and uuid_type == UuidType.DELEGATOR

def _check_all_delegators(uuid, uuid_type, resource_uuid):
    return uuid_type == UuidType.DELEGATOR

_permission_checker = {
    Permission.CUSTOMER_OWNER: _check_customer_owner,
    Permission.DELEGATOR_OWNER: _check_delegator_owner,
    Permission.ALL_DELEGATORS: _check_all_delegators,
}
