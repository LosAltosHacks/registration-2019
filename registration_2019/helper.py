import jwt
import uuid
import re
import datetime
import time
import enum
from argparse import ArgumentTypeError
from flask_restful.reqparse import RequestParser
from .core import app

def rand_uuid():
    return str(uuid.uuid4())

def nil(type):
    def predicate(x):
        if x == False:
            return False
        elif not x: # empty string, empty dict, etc
            return None
        else:
            return type(x)
    return predicate

def boolean(x):
    if x in [True, False]:
        return x

    raise ArgumentTypeError("Argument must be a boolean")

def strn(x):
    if type(x) is not str:
        raise ArgumentTypeError("Argument must be a string")
    if not x:
        raise ArgumentTypeError("String cannot be empty")

    return x

def help_jsonify(x):
    if issubclass(type(x), enum.Enum):
        return x.value

    if type(x) is datetime.datetime:
        return str(x)

    return x

# kwargs can contain a 'description' to return in the message
def or_types(*args, **kwargs):
    def convert(x):
        for arg in args:
            try:
                if type(x) is arg:
                    return x

                # assume valid unless exception is thrown
                return arg(x)
            except Exception:
                pass

        raise ArgumentTypeError(kwargs.get('description', "Couldn't parse request"))

    return convert

def re_matches(regex, description, group=None):
    def matcher(s):
        groups = re.search(regex, s)

        if not groups:
            raise ArgumentTypeError("String does not match regex for " + description)

        if group:
            return groups.group(group)
        else:
            return s

    return matcher

# regex standard for email addresses as defined by RFC 5322
email_string = re_matches("(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21\\x23-\\x5b\\x5d-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21-\\x5a\\x53-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])+)\\])", "email")

# regex for UUID
user_id_string = re_matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "user_id")

# regex for "Bearer <token>"
jwt_string = re_matches("Bearer ([a-zA-Z0-9._\-]+)$", "authentication token", 1)

def current_millis():
    return int(round(time.time() * 1000))

def is_authenticated(token):

    try:
        decoded = jwt.decode(token, app.config['JWT_SECRET'])
    except:
        # on any decoding exceptions etc
        return False

    expiration = decoded['expiration']
    email      = decoded['email']
    is_lah     = decoded['is_lah']

    # can perform additional verification here based on the specific email, etc

    # not expired, and has an lah domain
    return expiration > current_millis() and is_lah

def create_jwt(email):

    expiration = current_millis() + (1000 * 60 * 60 * 24) # one day in the future

    domain = email.split('@')[1]
    is_lah = domain == "losaltoshacks.com"

    return jwt.encode({'email': email, 'expiration': expiration, 'is_lah': is_lah}, app.config['JWT_SECRET']).decode('utf-8')

def copy_row(model, row, ignored_columns=[], overwrite={}):
    copy = model()

    changed = False
    for col in row.__table__.columns:
        k = col.name
        v = getattr(row, col.name)

        if k not in ignored_columns:
            ow = overwrite.get(k)
            if ow:
                copy.__setattr__(k, ow)
                if ow != v:
                    changed = True
            else:
                copy.__setattr__(k, v)

    return copy, changed

def remove_none_values(dictionary):
    return {k: v for k, v in dictionary.items() if v is not None}

def select_keys(dictionary, keys):
    if type(dictionary) is not dict:
        dictionary = dictionary.__dict__
    return {k: dictionary.get(k) for k in keys}

def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()
