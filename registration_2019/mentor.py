import datetime
import enum
from sqlalchemy import Column, String, SmallInteger, Integer, Enum, Boolean, ForeignKey, DateTime
from flask import redirect
from flask_restful import Resource, reqparse
from .core import api, db, app
from .helper import *
from .authentication import auth
from .emailing import send_email_template
from .registration import TShirtSizeEnum, AcceptanceStatusEnum

## Models

class MentorEmailVerification(db.Model):
    id          = Column(Integer,     nullable=False, primary_key=True)
    mentor_id   = Column(String(36),  nullable=False)
    email       = Column(String(255), nullable=False)
    email_token = Column(String(36),  nullable=False, default=rand_uuid)
    verified    = Column(Boolean,     nullable=False, default=False)

class Mentor(db.Model):
    id                    = Column(Integer,                    nullable=False, primary_key=True)
    mentor_id             = Column(String(36),                 nullable=False, default=rand_uuid)
    name                  = Column(String(255),                nullable=False)
    phone                 = Column(String(255),                nullable=False)
    email                 = Column(String(255),                nullable=False)
    over_18               = Column(Boolean,                    nullable=False)
    skillset              = Column(String(1000))
    tshirt_size           = Column(Enum(TShirtSizeEnum),       nullable=False)
    dietary_restrictions  = Column(String(255))
    email_verification_id = Column(Integer,                    ForeignKey(MentorEmailVerification.id))
    acceptance_status     = Column(Enum(AcceptanceStatusEnum), nullable=False, default=AcceptanceStatusEnum.none)
    signed_waiver         = Column(Boolean,                    nullable=False, default=False)
    outdated              = Column(Boolean,                    nullable=False, default=False)
    timestamp             = Column(DateTime,                   nullable=False, default=datetime.datetime.utcnow)

    email_verification    = db.relationship('MentorEmailVerification', foreign_keys='Mentor.email_verification_id')

    def as_dict(self):
        result = {c.name: help_jsonify(getattr(self, c.name)) for c in self.__table__.columns}
        result['email_verified'] = self.email_verification.verified
        return result

## Helper Functions

def email_in_use(new_email):
    return Mentor.query.filter_by(email=new_email, outdated=False).count() > 0

def clean_mentor(mentor, extra=[]):
    return select_keys(mentor.as_dict(), ['mentor_id', 'name', 'email', 'phone',
                                          'tshirt_size', 'dietary_restrictions', 'signed_waiver',
                                          'acceptance_status', 'email_verified', 'timestamp', *extra])

def send_email(mentor, template):
    email_data = select_keys(mentor.as_dict(), ['mentor_id', 'name', 'email', 'phone'
                                                'tshirt_size', 'dietary_restrictions', 'signed_waiver',
                                                'acceptance_status'])

    full_data = {**email_data, 'full_name': mentor.name, 'email_verification_token': mentor.email_verification.email_token}
    # TODO send_email_template(full_data, template)

def add_mentor(mentor):
    db.session.add(mentor)

    email_verification = MentorEmailVerification.query.filter_by(email=mentor.email, mentor_id=mentor.mentor_id).scalar()

    if not email_verification:
        email_verification = MentorEmailVerification(mentor_id=mentor.mentor_id, email=mentor.email)
        db.session.add(email_verification)
        db.session.commit()

    # add the email verification reference
    mentor.email_verification_id = email_verification.id
    db.session.commit()

    if not mentor.email_verification.verified:
        send_email(mentor, "mentor_confirmation")

def modify(mentor_id, delta):

    # find the most recent mentor for mentor_id
    old_mentor = Mentor.query.filter_by(mentor_id=mentor_id, outdated=False).scalar()

    if not old_mentor:
        return {"message": "User does not exist"}, 400

    new_mentor, changed = copy_row(Mentor, old_mentor, ignored_columns=['id', 'outdated', 'timestamp', 'email_verified'], overwrite=delta)

    email_verified = delta.get('email_verified')
    new_verified = email_verified is not None and email_verified != old_mentor.email_verification.verified

    # no changes, just return
    if not changed and not new_verified:
        return {"status": "ok", "message": "unchanged"}

    # validate new data

    if old_mentor.email != new_mentor.email and email_in_use(new_mentor.email):
        # ok to leak "email in use" here, modify is auth'd and only used by the team
        return {"message": "Email already in use"}, 400

    # validated, update the data
    if changed:
        old_mentor.outdated = True
        add_mentor(new_mentor)

        if new_verified:
            new_mentor.email_verification.verified = email_verified
    elif new_verified:
        # only change is email verification, no new mentor will be created (since verification is in a separate table)
        old_mentor.email_verification.verified = email_verified

    db.session.commit()

    return {"status": "ok"}

def search(query):

    if not query:
        return []
    elif type(query) is str:
        results = Mentor.query.filter((Mentor.mentor_id == query) |
                                      Mentor.name.contains(query) |
                                      Mentor.email.contains(query) |
                                      Mentor.phone.contains(query)).all()

        return [clean_mentor(x, extra=['outdated']) for x in results]
    else:
        query = remove_none_values(query)
        email_verified = query.get('email_verified')
        outdated = query.get('outdated')

        if email_verified is not None:
            query.pop('email_verified')

        if outdated == '*':
            query.pop('outdated')

        if outdated is None:
            results = Mentor.query.filter_by(**query, outdated=False)
        else:
            results = Mentor.query.filter_by(**query)

        return [clean_mentor(x,
                             # include `outdated` field if it was provided in the request
                             extra=(['outdated'] if outdated is not None else []))
                for x in results
                # have to manually check the email verification if it was provided, since it's in another table
                if (email_verified is None or
                    x.email_verification.verified == email_verified)]

def list():
    return [clean_mentor(x) for x in Mentor.query.filter_by(outdated=False)]

def history(mentor_id):
    mentors = Mentor.query.filter_by(mentor_id=mentor_id)

    if mentors.count() == 0:
        return {"message": "Mentor does not exist"}, 400
    else:
        return [clean_mentor(x, extra=['outdated']) for x in mentors]

def delete(mentor_id):
        mentor = Mentor.query.filter_by(mentor_id=mentor_id, outdated=False).scalar()
        if not mentor:
            return {"message": "Mentor does not exist"}, 400

        else:
            mentor.outdated=True
            db.session.commit()
            return {"status": "ok"}

## Endpoints

class MentorEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('name',                  type=strn,           required=True)
        self.parser.add_argument('phone',                 type=strn,           required=True)
        self.parser.add_argument('email',                 type=email_string,   required=True)
        self.parser.add_argument('over_18',               type=bool,           required=True)
        self.parser.add_argument('skillset',              type=strn,           required=True)
        self.parser.add_argument('tshirt_size',           type=TShirtSizeEnum, required=True)
        self.parser.add_argument('dietary_restrictions',  type=strn)

    def post(self):

        args = self.parser.parse_args()

        if email_in_use(args['email']):
            mentor = Mentor.query.filter_by(email=args['email'], outdated=False).scalar()
            #send_email(mentor, "reregistered") # TODO: Send reregistered email
            return {"status": "ok"}

        add_mentor(Mentor(**args))

        return {"status": "ok"}

class MentorVerifyEndpoint(Resource):

    def get(self, mentor_id, email_token):
        email_verification = MentorEmailVerification.query.filter_by(mentor_id=mentor_id, email_token=email_token).scalar()

        if email_verification:
            email_verification.verified = True
            db.session.commit()
            return redirect(app.config['CONFIRMATION_REDIRECT'])
        else:
            return {"message": "Could not verify"}, 422

class MentorModifyEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('name',                  type=strn)
        self.parser.add_argument('email',                 type=email_string)
        self.parser.add_argument('phone',                 type=strn)
        self.parser.add_argument('over_18',               type=bool)
        self.parser.add_argument('skkillset',             type=strn)
        self.parser.add_argument('tshirt_size',           type=TShirtSizeEnum)
        self.parser.add_argument('dietary_restrictions',  type=strn)
        self.parser.add_argument('acceptance_status',     type=AcceptanceStatusEnum)
        self.parser.add_argument('signed_waiver',         type=bool)
        self.parser.add_argument('email_verified',        type=bool)

    @auth
    def post(self, mentor_id):
        args = self.parser.parse_args()
        return modify(mentor_id, args)

class MentorSearchEndpoint(Resource):

    parser = reqparse.RequestParser()
    nested_parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('query', type=or_types(strn, dict), required=True)

        self.nested_parser.add_argument('mentor_id',             type=user_id_string,          location='query')
        self.nested_parser.add_argument('name',                  type=strn,                    location='query')
        self.nested_parser.add_argument('email',                 type=email_string,            location='query')
        self.nested_parser.add_argument('phone',                 type=strn,                    location='query')
        self.nested_parser.add_argument('tshirt_size',           type=TShirtSizeEnum,          location='query')
        self.nested_parser.add_argument('signed_waiver',         type=bool,                    location='query')
        self.nested_parser.add_argument('dietary_restrictions',  type=strn,                    location='query')
        self.nested_parser.add_argument('acceptance_status',     type=AcceptanceStatusEnum,    location='query')
        self.nested_parser.add_argument('email_verified',        type=bool,                    location='query')
        self.nested_parser.add_argument('outdated',              type=or_types(boolean, strn), location='query')

    @auth
    def post(self):
        args = self.parser.parse_args()

        query = args['query']

        # parse as Mentor dict if provided
        if type(query) is dict:
            query = self.nested_parser.parse_args(req=args)

        return search(query)

class MentorListEndpoint(Resource):

    @auth
    def get(self):
        return list()

class MentorHistoryEndpoint(Resource):

    @auth
    def get(self, mentor_id):
        return history(mentor_id)

class MentorDeleteEndpoint(Resource):

    @auth
    def get(self, mentor_id):
        return delete(mentor_id)

# TODO: waiver Callback (after being accepted, applicants will need to sign a waiver through a third party)

api.add_resource(MentorEndpoint,  '/mentor/v1/signup')
api.add_resource(MentorVerifyEndpoint,  '/mentor/v1/verify/<mentor_id>/<email_token>')
api.add_resource(MentorModifyEndpoint,  '/mentor/v1/modify/<mentor_id>')
api.add_resource(MentorListEndpoint,    '/mentor/v1/list')
api.add_resource(MentorSearchEndpoint,  '/mentor/v1/search')
api.add_resource(MentorHistoryEndpoint, '/mentor/v1/history/<mentor_id>')
api.add_resource(MentorDeleteEndpoint,  '/mentor/v1/delete/<mentor_id>')
