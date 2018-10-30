import os
from flask_restful import Resource, reqparse
from .core import api, db
from .authentication import auth
from .helper import email_string

## Models

class EmailSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

## Endpoints

class Subscribe(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):
        self.parser.add_argument('email', type=email_string, required=True)

    def post(self):

        req_email = self.parser.parse_args()['email']

        sub = EmailSubscription.query.filter_by(email=req_email).first()

        if sub == None:
            new_sub = EmailSubscription(email=req_email)
            db.session.add(new_sub)
            db.session.commit()

        return {"status": "ok"}

class Subscriptions(Resource):

    @auth
    def get(self):
        return [x.email for x in EmailSubscription.query.all()]

## Register endpoints

api.add_resource(Subscribe, '/email_list/v1/subscribe')
api.add_resource(Subscriptions, '/email_list/v1/subscriptions')
