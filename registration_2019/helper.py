import jwt
import uuid
import re
import time
from argparse import ArgumentTypeError
from .core import app

def rand_uuid():
    return str(uuid.uuid4())

def strn(x):
    if type(x) is not str:
        raise ArgumentTypeError("Argument must be a string")
    if not x:
        raise ArgumentTypeError("String cannot be empty")

    return x

def email(s):

    # regex standard for email addresses as defined by RFC 5322
    if not re.match("(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21\\x23-\\x5b\\x5d-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21-\\x5a\\x53-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])+)\\])", s):
        raise ArgumentTypeError("Invalid format for email address")
    return s

def current_millis():
    return int(round(time.time() * 1000))

def jwt_string(s):

    # regex to match JWT tokens
    groups = re.search("Bearer ([a-zA-Z0-9._\-]+)$", s)
    if not groups:
        raise ArgumentTypeError("Invalid format for JWT")

    # extract the token
    return groups[1]

def is_authenticated(token):

    try:
        decoded = jwt.decode(token, app.config['JWT_SECRET'])
    except:
        # on any decoding exceptions etc
        return False

    expiration = decoded['expiration']
    email      = decoded['email']
    is_lah     = decoded['is_lah']

    # not expired, and has an lah domain
    return expiration > current_millis() and is_lah

def create_jwt(email):

    expiration = current_millis() + (1000 * 60 * 60 * 24) # one day in the future

    domain = email.split('@')[1]
    is_lah = domain == "losaltoshacks.com"

    return jwt.encode({'email': email, 'expiration': expiration, 'is_lah': is_lah}, app.config['JWT_SECRET']).decode('utf-8')

def copy_row(model, row, ignored_columns=[]):
    copy = model()

    for col in row.__table__.columns:
        if col.name not in ignored_columns:
            copy.__setattr__(col.name, getattr(row, col.name))

    return copy
