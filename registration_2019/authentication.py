import jwt
import re
from flask_restful import Resource, reqparse, abort
from argparse import ArgumentTypeError
from google.oauth2 import id_token
from google.auth.transport import requests
from .core import app, api
from .helper import jwt_string, create_jwt, is_authenticated, strn

# @auth decorator

auth_parser = reqparse.RequestParser()
auth_parser.add_argument('authorization', type=jwt_string, required=True, location='headers')

def auth(f):
    def wrapper(*args, **kwargs):

        token = auth_parser.parse_args()['authorization']

        if not app.config.get('DISABLE_AUTHENTICATION') and not is_authenticated(token):
            abort(401, description="Not authenticated")

        return f(*args, **kwargs)
    return wrapper

# endpoints

class Login(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):
        self.parser.add_argument('token', type=strn, required=True)

    def post(self):
        args = self.parser.parse_args()
        token = args['token']

        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), app.config['GOOGLE_CLIENT_ID'])
        except:
            return {"message": "Could not authenticate"}, 401

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com'] or idinfo['hd'] != app.config['GSUITE_DOMAIN_NAME']:
            return {"message": "Could not authenticate"}, 401

        email_address = idinfo['email']
        jwt = create_jwt(email_address)

        return {"jwt": jwt}

# register endpoints

api.add_resource(Login, '/oauth/v1/login')
