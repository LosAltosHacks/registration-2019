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

class Chaperone(db.Model):
    id                    = Column(Integer,                    nullable=False, primary_key=True)
    chaperone_id          = Column(String(36),                 nullable=False, default=rand_uuid)
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
    return Chaperone.query.filter_by(email=new_email, outdated=False).count() > 0

def clean_chaperone(chaperone, extra=[]):
    return select_keys(chaperone.as_dict(), ['chaperone_id', 'name', 'email', 'phone',
                                          'signed_waiver', 'timestamp', 'kind', *extra])


def add_chaperone(chaperone):
    db.session.add(chaperone)
    db.session.commit()

def modify(chaperone_id, delta):

    # find the most recent chaperone for chaperone_id
    old_chaperone = Chaperone.query.filter_by(chaperone_id=chaperone_id, outdated=False).scalar()

    if not old_chaperone:
        return {"message": "Chaperone does not exist"}, 400

    new_chaperone, changed = copy_row(Chaperone, old_chaperone, ignored_columns=['id', 'outdated', 'timestamp'], overwrite=delta)

    # no changes, just return
    if not changed and not new_verified:
        return {"status": "ok", "message": "unchanged"}

    # validate new data
    if old_chaperone.email != new_chaperone.email and email_in_use(new_chaperone.email):
        # ok to leak "email in use" here, modify is auth'd and only used by the team
        return {"message": "Email already in use"}, 400

    # validated, update the data
    if changed:
        old_chaperone.outdated = True
        add_chaperone(new_chaperone)

    db.session.commit()

    return {"status": "ok"}

def search(query):

    if not query:
        return []
    elif type(query) is str:
        results = Chaperone.query.filter((Chaperone.chaperone_id == query) |
                                          Chaperone.name.contains(query) |
                                          Chaperone.email.contains(query) |
                                          Chaperone.phone.contains(query)).all()

        return [clean_chaperone(x, extra=['outdated']) for x in results]
    else:
        query = remove_none_values(query)
        outdated = query.get('outdated')

        if outdated == '*':
            query.pop('outdated')

        if outdated is None:
            results = Chaperone.query.filter_by(**query, outdated=False)
        else:
            results = Chaperone.query.filter_by(**query)

        return [clean_chaperone(x,
                             # include `outdated` field if it was provided in the request
                             extra=(['outdated'] if outdated is not None else []))
                for x in results]

def list():
    return [clean_chaperone(x) for x in Chaperone.query.filter_by(outdated=False)]

def delete(chaperone_id):
        chaperone = Chaperone.query.filter_by(chaperone_id=chaperone_id, outdated=False).scalar()
        if not chaperone:
            return {"message": "Chaperone does not exist"}, 400

        else:
            chaperone.outdated=True
            db.session.commit()
            return {"status": "ok"}

## Endpoints

class ChaperoneEndpoint(Resource):

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
            chaperone = Chaperone.query.filter_by(email=args['email'], outdated=False).scalar()
            return {"status": "ok",
                    "message": "chaperone already added (by email)"}

        add_chaperone(Chaperone(**args))

        return {"status": "ok"}

class ChaperoneModifyEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('name',                  type=strn)
        self.parser.add_argument('email',                 type=email_string)
        self.parser.add_argument('phone',                 type=strn)
        self.parser.add_argument('signed_waiver',         type=bool)
        self.parser.add_argument('kind',                  type=GuestKindEnum)

    @auth
    def post(self, chaperone_id):
        args = self.parser.parse_args()
        return modify(chaperone_id, args)

class ChaperoneSearchEndpoint(Resource):

    parser = reqparse.RequestParser()
    nested_parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('query', type=or_types(strn, dict), required=True)

        self.nested_parser.add_argument('chaperone_id',          type=user_id_string,          location='query')
        self.nested_parser.add_argument('name',                  type=strn,                    location='query')
        self.nested_parser.add_argument('email',                 type=email_string,            location='query')
        self.nested_parser.add_argument('phone',                 type=strn,                    location='query')
        self.nested_parser.add_argument('signed_waiver',         type=bool,                    location='query')
        self.nested_parser.add_argument('outdated',              type=or_types(boolean, strn), location='query')

    @auth
    def post(self):
        args = self.parser.parse_args()

        query = args['query']

        # parse as Chaperone dict if provided
        if type(query) is dict:
            query = self.nested_parser.parse_args(req=args)

        return search(query)

class ChaperoneListEndpoint(Resource):

    @auth
    def get(self):
        return list()

class ChaperoneDeleteEndpoint(Resource):

    @auth
    def get(self, chaperone_id):
        return delete(chaperone_id)

# TODO: waiver Callback

api.add_resource(ChaperoneEndpoint,        '/chaperone/v1/signup')
api.add_resource(ChaperoneModifyEndpoint,  '/chaperone/v1/modify/<chaperone_id>')
api.add_resource(ChaperoneListEndpoint,    '/chaperone/v1/list')
api.add_resource(ChaperoneSearchEndpoint,  '/chaperone/v1/search')
api.add_resource(ChaperoneDeleteEndpoint,  '/chaperone/v1/delete/<chaperone_id>')
