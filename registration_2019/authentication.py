import jwt
import re
from flask_restful import Resource, reqparse, abort
from argparse import ArgumentTypeError
from .core import app, api
from .helper import jwt_string, create_jwt, is_authenticated, strn

# @auth decorator

auth_parser = reqparse.RequestParser()
auth_parser.add_argument('authorization', type=jwt_string, required=True, location='headers')

def auth(f):
    def wrapper(*args, **kwargs):

        token = auth_parser.parse_args()['authorization']

        if not is_authenticated(token):
            abort(401, description="Not authenticated")

        return f(*args, **kwargs)
    return wrapper

# endpoints

# WARNING: THIS IS CURRENTLY INCOMPLETE AND EXPOSED FOR DEVELOPMENT PURPOSES
class Login(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):
        self.parser.add_argument('code', type=strn, required=True) # NV TODO: change type back to string, and implement oauth with GSuite

    def post(self):
        args = self.parser.parse_args()
        code = args['code']
        return {"jwt": create_jwt(code)}

# register endpoints

api.add_resource(Login, '/oauth/v1/login')
