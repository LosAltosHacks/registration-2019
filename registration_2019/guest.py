import datetime
import enum
from sqlalchemy import Column, String, SmallInteger, Integer, Enum, Boolean, ForeignKey, DateTime
from flask import redirect
from flask_restful import Resource, reqparse
from .core import api, db, app
from .helper import *
from .authentication import auth

## Models
class GuestKindEnum(enum.Enum):
    sponsor    = "sponsor"
    chaperone  = "chaperone"
    judge      = "judge"

class Guest(db.Model):
    id                    = Column(Integer,                    nullable=False, primary_key=True)
    guest_id              = Column(String(36),                 nullable=False, default=rand_uuid)
    name                  = Column(String(255),                nullable=False)
    phone                 = Column(String(255),                nullable=True)
    email                 = Column(String(255),                nullable=False)
    kind                  = Column(Enum(GuestKindEnum),        nullable=False)
    signed_waiver         = Column(Boolean,                    nullable=False, default=False)
    outdated              = Column(Boolean,                    nullable=False, default=False)
    timestamp             = Column(DateTime,                   nullable=False, default=datetime.datetime.utcnow)

    def as_dict(self):
        result = {c.name: help_jsonify(getattr(self, c.name)) for c in self.__table__.columns}
        return result

## Helper Functions

def email_in_use(new_email):
    return Guest.query.filter_by(email=new_email, outdated=False).count() > 0

def clean_guest(guest, extra=[]):
    return select_keys(guest.as_dict(), ['guest_id', 'name', 'email', 'phone',
                                         'signed_waiver', 'timestamp', 'kind', *extra])


def add_guest(guest):
    db.session.add(guest)
    db.session.commit()

def modify(guest_id, delta):

    # find the most recent guest for guest_id
    old_guest = Guest.query.filter_by(guest_id=guest_id, outdated=False).scalar()

    if not old_guest:
        return {"message": "Guest does not exist"}, 400

    new_guest, changed = copy_row(Guest, old_guest, ignored_columns=['id', 'outdated', 'timestamp'], overwrite=delta)

    # no changes, just return
    if not changed and not new_verified:
        return {"status": "ok", "message": "unchanged"}

    # validate new data
    if old_guest.email != new_guest.email and email_in_use(new_guest.email):
        # ok to leak "email in use" here, modify is auth'd and only used by the team
        return {"message": "Email already in use"}, 400

    # validated, update the data
    if changed:
        old_guest.outdated = True
        add_gues(new_guest)

    db.session.commit()

    return {"status": "ok"}

def search(query):

    if not query:
        return []
    elif type(query) is str:
        results = Guest.query.filter((Guest.guest_id == query) |
                                      Guest.name.contains(query) |
                                      Guest.email.contains(query) |
                                      Guest.phone.contains(query)).all()

        return [clean_guest(x, extra=['outdated']) for x in results]
    else:
        query = remove_none_values(query)
        outdated = query.get('outdated')

        if outdated == '*':
            query.pop('outdated')

        if outdated is None:
            results = Guest.query.filter_by(**query, outdated=False)
        else:
            results = Guest.query.filter_by(**query)

        return [clean_guest(x,
                             # include `outdated` field if it was provided in the request
                             extra=(['outdated'] if outdated is not None else []))
                for x in results]

def list():
    return [clean_guest(x) for x in Guest.query.filter_by(outdated=False)]

def delete(guest_id):
        guest = Guest.query.filter_by(guest_id=guest_id, outdated=False).scalar()
        if not guest:
            return {"message": "Guest does not exist"}, 400

        else:
            guest.outdated=True
            db.session.commit()
            return {"status": "ok"}

## Endpoints

class GuestEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('name',                  type=strn,           required=True)
        self.parser.add_argument('phone',                 type=strn,           required=False)
        self.parser.add_argument('email',                 type=email_string,   required=True)
        self.parser.add_argument('kind',                  type=GuestKindEnum,  required=True)

    @auth
    def post(self):

        args = self.parser.parse_args()

        if email_in_use(args['email']):
            guest = Guest.query.filter_by(email=args['email'], outdated=False).scalar()
            return {"status": "ok",
                    "message": "Guest already added (by email)"}

        add_guest(Guest(**args))

        return {"status": "ok"}

class GuestModifyEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('name',                  type=strn)
        self.parser.add_argument('email',                 type=email_string)
        self.parser.add_argument('phone',                 type=strn)
        self.parser.add_argument('signed_waiver',         type=bool)
        self.parser.add_argument('kind',                  type=GuestKindEnum)

    @auth
    def post(self, guest_id):
        args = self.parser.parse_args()
        return modify(guest_id, args)

class GuestSearchEndpoint(Resource):

    parser = reqparse.RequestParser()
    nested_parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('query', type=or_types(strn, dict), required=True)

        self.nested_parser.add_argument('guest_id',              type=user_id_string,          location='query')
        self.nested_parser.add_argument('name',                  type=strn,                    location='query')
        self.nested_parser.add_argument('email',                 type=email_string,            location='query')
        self.nested_parser.add_argument('phone',                 type=strn,                    location='query')
        self.nested_parser.add_argument('signed_waiver',         type=bool,                    location='query')
        self.nested_parser.add_argument('outdated',              type=or_types(boolean, strn), location='query')

    @auth
    def post(self):
        args = self.parser.parse_args()

        query = args['query']

        # parse as Guest dict if provided
        if type(query) is dict:
            query = self.nested_parser.parse_args(req=args)

        return search(query)

class GuestListEndpoint(Resource):

    @auth
    def get(self):
        return list()

class GuestDeleteEndpoint(Resource):

    @auth
    def get(self, guest_id):
        return delete(guest_id)

# TODO: waiver Callback

api.add_resource(GuestEndpoint,        '/guest/v1/signup')
api.add_resource(GuestModifyEndpoint,  '/guest/v1/modify/<guest_id>')
api.add_resource(GuestListEndpoint,    '/guest/v1/list')
api.add_resource(GuestSearchEndpoint,  '/guest/v1/search')
api.add_resource(GuestDeleteEndpoint,  '/guest/v1/delete/<guest_id>')
