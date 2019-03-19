import datetime
import enum
from sqlalchemy import Column, String, SmallInteger, Integer, Enum, Boolean, ForeignKey, DateTime
from flask import redirect
from flask_restful import Resource, reqparse
from .core import api, db, app
from .helper import *
from .authentication import auth
from .emailing import send_email_template
from .dayof_model import SignIn

## Models

class TShirtSizeEnum(enum.Enum):
    small       = "S"
    medium      = "M"
    large       = "L"
    extra_large = "XL"

class AcceptanceStatusEnum(enum.Enum):
    none       = "none"
    waitlist_queue = "waitlist_queue"
    waitlisted = "waitlisted"
    rejected   = "rejected"
    queue      = "queue"
    accepted   = "accepted"

class EmailVerification(db.Model):
    id          = Column(Integer,     nullable=False, primary_key=True)
    user_id     = Column(String(36),  nullable=False)
    email       = Column(String(255), nullable=False)
    email_token = Column(String(36),  nullable=False, default=rand_uuid)
    verified    = Column(Boolean,     nullable=False, default=False)

class Signup(db.Model):
    id                    = Column(Integer,                    nullable=False, primary_key=True)
    user_id               = Column(String(36),                 nullable=False, default=rand_uuid)
    first_name            = Column(String(255),                nullable=False)
    surname               = Column(String(255),                nullable=False)
    email                 = Column(String(255),                nullable=False)
    age                   = Column(SmallInteger,               nullable=False)
    school                = Column(String(255),                nullable=False)
    grade                 = Column(SmallInteger,               nullable=False)
    student_phone_number  = Column(String(255),                nullable=False)
    gender                = Column(String(255),                nullable=False)
    ethnicity             = Column(String(255))
    tshirt_size           = Column(Enum(TShirtSizeEnum),       nullable=False)
    previous_hackathons   = Column(SmallInteger,               nullable=False)
    guardian_name         = Column(String(255))
    guardian_email        = Column(String(255))
    guardian_phone_number = Column(String(255))
    github_username       = Column(String(255))
    linkedin_profile      = Column(String(255))
    dietary_restrictions  = Column(String(255))
    signed_waiver         = Column(Boolean,                    nullable=False, default=False)
    email_verification_id = Column(Integer,                    ForeignKey(EmailVerification.id))
    sign_in_id            = Column(Integer,                    ForeignKey(SignIn.id), nullable=True)
    acceptance_status     = Column(Enum(AcceptanceStatusEnum), nullable=False, default=AcceptanceStatusEnum.none)
    outdated              = Column(Boolean,                    nullable=False, default=False)
    timestamp             = Column(DateTime,                   nullable=False, default=datetime.datetime.utcnow)

    email_verification    = db.relationship('EmailVerification', foreign_keys='Signup.email_verification_id')
    sign_in                = db.relationship('SignIn', foreign_keys='Signup.sign_in_id')

    def as_dict(self):
        result = {c.name: help_jsonify(getattr(self, c.name)) for c in self.__table__.columns}
        result['email_verified'] = self.email_verification.verified
        result['signed_in'] = self.sign_in is not None
        return result

## Helper Functions

def invalid_age(args):
    return args['age'] < 18 and not (args['guardian_name'] and args['guardian_email'] and args['guardian_phone_number'])

def email_in_use(new_email):
    return Signup.query.filter_by(email=new_email, outdated=False).count() > 0

def clean_signup(signup, extra=[]):
    return select_keys(signup.as_dict(), ['user_id', 'first_name', 'surname', 'email', 'age', 'school',
                                          'grade', 'student_phone_number', 'guardian_name',
                                          'guardian_email', 'guardian_phone_number', 'gender', 'ethnicity',
                                          'tshirt_size', 'previous_hackathons', 'github_username',
                                          'linkedin_profile', 'dietary_restrictions', 'signed_waiver',
                                          'acceptance_status', 'email_verified', 'signed_in', 'timestamp', *extra])

def send_email(signup, template):
    full_name = signup.first_name + " " + signup.surname
    email_data = select_keys(signup.as_dict(), ['user_id', 'first_name', 'surname', 'email', 'age', 'school',
                                                'grade', 'student_phone_number', 'guardian_name',
                                                'guardian_email', 'guardian_phone_number', 'gender', 'ethnicity',
                                                'tshirt_size', 'dietary_restrictions', 'signed_waiver',
                                                'acceptance_status'])

    full_data = {**email_data, 'full_name': full_name, 'email_verification_token': signup.email_verification.email_token}
    send_email_template(full_data, template)

def add_signup(signup):
    db.session.add(signup)

    email_verification = EmailVerification.query.filter_by(email=signup.email, user_id=signup.user_id).scalar()

    if not email_verification:
        email_verification = EmailVerification(user_id=signup.user_id, email=signup.email)
        db.session.add(email_verification)
        db.session.commit()

    # add the email verification reference
    signup.email_verification_id = email_verification.id
    db.session.commit()

    if not signup.email_verification.verified:
        send_email(signup, "confirmation")

def modify(user_id, delta):

    # find the most recent signup for user_id
    old_signup = Signup.query.filter_by(user_id=user_id, outdated=False).scalar()

    if not old_signup:
        return {"message": "User does not exist"}, 400

    new_signup, changed = copy_row(Signup, old_signup, ignored_columns=['id', 'outdated', 'timestamp', 'email_verified'], overwrite=delta)

    email_verified = delta.get('email_verified')
    new_verified = email_verified is not None and email_verified != old_signup.email_verification.verified

    # no changes, just return
    if not changed and not new_verified:
        return {"status": "ok", "message": "unchanged"}

    # validate new data

    if invalid_age(new_signup.__dict__):
        return {"message": "Minors must provide guardian information"}, 400

    if old_signup.email != new_signup.email and email_in_use(new_signup.email):
        # ok to leak "email in use" here, modify is auth'd and only used by the team
        return {"message": "Email already in use"}, 400

    # validated, update the data
    if changed:
        old_signup.outdated = True
        add_signup(new_signup)

        if new_verified:
            new_signup.email_verification.verified = email_verified
    elif new_verified:
        # only change is email verification, no new signup will be created (since verification is in a separate table)
        old_signup.email_verification.verified = email_verified

    db.session.commit()

    return {"status": "ok"}

def search(query):

    if not query:
        return []
    elif type(query) is str:
        results = Signup.query.filter((Signup.user_id == query) |
                                      Signup.first_name.contains(query) |
                                      Signup.surname.contains(query) |
                                      Signup.email.contains(query) |
                                      Signup.student_phone_number.contains(query) |
                                      Signup.guardian_name.contains(query) |
                                      Signup.guardian_email.contains(query) |
                                      Signup.guardian_phone_number.contains(query)).all()

        return [clean_signup(x, extra=['outdated']) for x in results]
    else:
        query = remove_none_values(query)
        email_verified = query.get('email_verified')
        outdated = query.get('outdated')

        if email_verified is not None:
            query.pop('email_verified')

        if outdated == '*':
            query.pop('outdated')

        if outdated is None:
            results = Signup.query.filter_by(**query, outdated=False)
        else:
            results = Signup.query.filter_by(**query)

        return [clean_signup(x,
                             # include `outdated` field if it was provided in the request
                             extra=(['outdated'] if outdated is not None else []))
                for x in results
                # have to manually check the email verification if it was provided, since it's in another table
                if (email_verified is None or
                    x.email_verification.verified == email_verified)]

def list():
    return [clean_signup(x) for x in Signup.query.filter_by(outdated=False)]

def history(user_id):
    signups = Signup.query.filter_by(user_id=user_id)

    if signups.count() == 0:
        return {"message": "User does not exist"}, 400
    else:
        return [clean_signup(x, extra=['outdated']) for x in signups]

def delete(user_id):
        signup = Signup.query.filter_by(user_id=user_id, outdated=False).scalar()
        if not signup:
            return {"message": "User does not exist"}, 400

        else:
            signup.outdated=True
            db.session.commit()
            return {"status": "ok"}

## Endpoints

class SignupEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        # TODO: Way to avoid repetition of all of these types?
        self.parser.add_argument('first_name',            type=strn,           required=True)
        self.parser.add_argument('surname',               type=strn,           required=True)
        self.parser.add_argument('email',                 type=email_string,   required=True)
        self.parser.add_argument('age',                   type=int,            required=True)
        self.parser.add_argument('school',                type=strn,           required=True)
        self.parser.add_argument('grade',                 type=int,            required=True)
        self.parser.add_argument('student_phone_number',  type=strn,           required=True)
        self.parser.add_argument('gender',                type=strn,           required=True)
        self.parser.add_argument('ethnicity',             type=strn)
        self.parser.add_argument('tshirt_size',           type=TShirtSizeEnum, required=True)
        self.parser.add_argument('previous_hackathons',   type=int,            required=True)
        self.parser.add_argument('guardian_name',         type=strn)
        self.parser.add_argument('guardian_email',        type=email_string)
        self.parser.add_argument('guardian_phone_number', type=strn)
        self.parser.add_argument('github_username',       type=strn)
        self.parser.add_argument('linkedin_profile',      type=strn)
        self.parser.add_argument('dietary_restrictions',  type=strn)

    def post(self):

        args = self.parser.parse_args()

        if invalid_age(args):
            return {"message": "Minors must provide guardian information"}, 400

        if email_in_use(args['email']):
            signup = Signup.query.filter_by(email=args['email'], outdated=False).scalar()
            #send_email(signup, "reregistered") # TODO: Send reregistered email
            return {"status": "ok"}

        add_signup(Signup(**args))

        return {"status": "ok"}

class VerifyEndpoint(Resource):

    def get(self, user_id, email_token):
        email_verification = EmailVerification.query.filter_by(user_id=user_id, email_token=email_token).scalar()

        if email_verification:
            email_verification.verified = True
            db.session.commit()
            return redirect(app.config['CONFIRMATION_REDIRECT'])
        else:
            return {"message": "Could not verify"}, 422

class ModifyEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('first_name',            type=strn)
        self.parser.add_argument('surname',               type=strn)
        self.parser.add_argument('email',                 type=email_string)
        self.parser.add_argument('age',                   type=int)
        self.parser.add_argument('school',                type=strn)
        self.parser.add_argument('grade',                 type=int)
        self.parser.add_argument('student_phone_number',  type=strn)
        self.parser.add_argument('gender',                type=strn)
        self.parser.add_argument('ethnicity',             type=strn)
        self.parser.add_argument('tshirt_size',           type=TShirtSizeEnum)
        self.parser.add_argument('previous_hackathons',   type=int)
        self.parser.add_argument('guardian_name',         type=nil(strn))          # guardian info can be None or empty string (when age is 18+)
        self.parser.add_argument('guardian_email',        type=nil(email_string))
        self.parser.add_argument('guardian_phone_number', type=nil(strn))
        self.parser.add_argument('github_username',       type=strn)
        self.parser.add_argument('linkedin_profile',      type=strn)
        self.parser.add_argument('dietary_restrictions',  type=strn)
        self.parser.add_argument('acceptance_status',     type=AcceptanceStatusEnum)
        self.parser.add_argument('email_verified',        type=bool)

    @auth
    def post(self, user_id):
        args = self.parser.parse_args()
        return modify(user_id, args)

class SearchEndpoint(Resource):

    parser = reqparse.RequestParser()
    nested_parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('query', type=or_types(strn, dict), required=True)

        self.nested_parser.add_argument('user_id',               type=user_id_string,          location='query')
        self.nested_parser.add_argument('first_name',            type=strn,                    location='query')
        self.nested_parser.add_argument('surname',               type=strn,                    location='query')
        self.nested_parser.add_argument('email',                 type=email_string,            location='query')
        self.nested_parser.add_argument('age',                   type=int,                     location='query')
        self.nested_parser.add_argument('school',                type=strn,                    location='query')
        self.nested_parser.add_argument('grade',                 type=int,                     location='query')
        self.nested_parser.add_argument('student_phone_number',  type=strn,                    location='query')
        self.nested_parser.add_argument('gender',                type=strn,                    location='query')
        self.nested_parser.add_argument('ethnicity',             type=strn,                    location='query')
        self.nested_parser.add_argument('tshirt_size',           type=TShirtSizeEnum,          location='query')
        self.nested_parser.add_argument('previous_hackathons',   type=int,                     location='query')
        # guardian info can be None or empty string (when age is 18+)
        self.nested_parser.add_argument('guardian_name',         type=nil(strn),               location='query')
        self.nested_parser.add_argument('guardian_email',        type=nil(email_string),       location='query')
        self.nested_parser.add_argument('guardian_phone_number', type=nil(strn),               location='query')
        self.nested_parser.add_argument('github_username',       type=strn,                    location='query')
        self.nested_parser.add_argument('linkedin_profile',      type=strn,                    location='query')
        self.nested_parser.add_argument('signed_waiver',         type=boolean,                 location='query')
        self.nested_parser.add_argument('dietary_restrictions',  type=strn,                    location='query')
        self.nested_parser.add_argument('acceptance_status',     type=AcceptanceStatusEnum,    location='query')
        self.nested_parser.add_argument('email_verified',        type=boolean,                 location='query')
        self.nested_parser.add_argument('outdated',              type=or_types(boolean, strn), location='query')

    @auth
    def post(self):
        args = self.parser.parse_args()

        query = args['query']

        # parse as Signup dict if provided
        if type(query) is dict:
            query = self.nested_parser.parse_args(req=args)

        return search(query)

class ListEndpoint(Resource):

    @auth
    def get(self):
        return list()

class HistoryEndpoint(Resource):

    @auth
    def get(self, user_id):
        return history(user_id)

class DeleteEndpoint(Resource):

    @auth
    def get(self, user_id):
        return delete(user_id)

# TODO: Add authenticated endpoint so that we can send custom emails via the admin dashboard? Might not be necessary, but worth a look into.

# TODO: waiver Callback (after being accepted, applicants will need to sign a waiver through a third party)

api.add_resource(SignupEndpoint,  '/registration/v1/signup')
api.add_resource(VerifyEndpoint,  '/registration/v1/verify/<user_id>/<email_token>')
api.add_resource(ModifyEndpoint,  '/registration/v1/modify/<user_id>')
api.add_resource(ListEndpoint,    '/registration/v1/list')
api.add_resource(SearchEndpoint,  '/registration/v1/search')
api.add_resource(HistoryEndpoint, '/registration/v1/history/<user_id>')
api.add_resource(DeleteEndpoint,  '/registration/v1/delete/<user_id>')
