import datetime
import enum
from sqlalchemy import Column, String, SmallInteger, Integer, Enum, Boolean, ForeignKey, DateTime
from flask_restful import Resource, reqparse
from .core import api, db
from .helper import rand_uuid, email, strn, copy_row
from .authentication import auth

## Models

class TShirtSizeEnum(enum.Enum):
    small       = "S"
    medium      = "M"
    large       = "L"
    extra_large = "XL"

class AcceptanceStatusEnum(enum.Enum):
    none       = "none"
    waitlisted = "waitlisted"
    rejected   = "rejected"
    queue      = "queue"
    accepted   = "accepted"

class SignupData(db.Model):
    id                    = Column(Integer,                    nullable=False, primary_key=True)
    user_id               = Column(String(36),                 nullable=False, default=rand_uuid)
    first_name            = Column(String(255),                nullable=False)
    surname               = Column(String(255),                nullable=False)
    email                 = Column(String(255),                nullable=False)
    age                   = Column(SmallInteger,               nullable=False)
    school                = Column(String(255),                nullable=False)
    grade                 = Column(SmallInteger,               nullable=False)
    student_phone_number  = Column(String(255),                nullable=False)
    guardian_name         = Column(String(255))
    guardian_email        = Column(String(255))
    guardian_phone_number = Column(String(255))
    gender                = Column(String(255),                nullable=False)
    tshirt_size           = Column(Enum(TShirtSizeEnum),       nullable=False)
    previous_hackathons   = Column(SmallInteger,               nullable=False)
    github_username       = Column(String(255))
    linkedin_profile      = Column(String(255))
    dietary_restrictions  = Column(String(255))
    signed_waver          = Column(Boolean,                    nullable=False, default=False)
    email_verified        = Column(Boolean,                    nullable=False, default=False)
    acceptance_status     = Column(Enum(AcceptanceStatusEnum), nullable=False, default=AcceptanceStatusEnum.none)
    outdated              = Column(Boolean,                    nullable=False, default=False)

class Signup(db.Model):
    id        = Column(Integer,    nullable=False,            primary_key=True)
    user_id   = Column(String(36), nullable=False)
    data_id   = Column(Integer,    ForeignKey(SignupData.id))
    timestamp = Column(DateTime,   nullable=False,            default=datetime.datetime.utcnow)

    data = db.relationship('SignupData', foreign_keys='Signup.data_id')

# NV TODO: Email verification

## Helper Functions

def invalid_age(args):
    return args['age'] < 18 and not (args['guardian_name'] and args['guardian_email'] and args['guardian_phone_number'])

def email_in_use(new_email):
    return SignupData.query.filter_by(email=new_email, outdated=False).count() > 0

## Endpoints

class SignupEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        # NV TODO: Way to automatically create this using the models defined above?
        self.parser.add_argument('first_name',            type=strn,           required=True)
        self.parser.add_argument('surname',               type=strn,           required=True)
        self.parser.add_argument('email',                 type=email,          required=True)
        self.parser.add_argument('age',                   type=int,            required=True)
        self.parser.add_argument('school',                type=strn,           required=True)
        self.parser.add_argument('grade',                 type=int,            required=True)
        self.parser.add_argument('student_phone_number',  type=strn,           required=True) # NV TODO: phone_number type
        self.parser.add_argument('guardian_name',         type=strn)
        self.parser.add_argument('guardian_email',        type=email)
        self.parser.add_argument('guardian_phone_number', type=strn) # NV TODO: phone_number type
        self.parser.add_argument('gender',                type=strn,           required=True)
        self.parser.add_argument('tshirt_size',           type=TShirtSizeEnum, required=True)
        self.parser.add_argument('previous_hackathons',   type=int,            required=True)
        self.parser.add_argument('github_username',       type=strn)
        self.parser.add_argument('linkedin_profile',      type=strn)
        self.parser.add_argument('dietary_restrictions',  type=strn)

    def post(self):

        args = self.parser.parse_args()

        if invalid_age(args):
            return {"message": "Minors must provide guardian information"}, 400

        if email_in_use(args['email']):
            return {"message": "Email already in use"}, 400 # NV TODO: Might not want to "leak" this info?

        data = SignupData(**args)
        db.session.add(data)
        db.session.commit()

        signup = Signup(user_id=data.user_id, data_id=data.id)

        db.session.add(signup)
        db.session.commit()

        return {"status": "ok"}

class ModifyEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('first_name',            type=strn)
        self.parser.add_argument('surname',               type=strn)
        self.parser.add_argument('email',                 type=email)
        self.parser.add_argument('age',                   type=int)
        self.parser.add_argument('school',                type=strn)
        self.parser.add_argument('grade',                 type=int)
        self.parser.add_argument('student_phone_number',  type=strn) # NV TODO: phone_number type
        self.parser.add_argument('guardian_name',         type=strn)
        self.parser.add_argument('guardian_email',        type=email)
        self.parser.add_argument('guardian_phone_number', type=strn) # NV TODO: phone_number type
        self.parser.add_argument('gender',                type=strn)
        self.parser.add_argument('tshirt_size',           type=TShirtSizeEnum)
        self.parser.add_argument('previous_hackathons',   type=int)
        self.parser.add_argument('github_username',       type=strn)
        self.parser.add_argument('linkedin_profile',      type=strn)
        self.parser.add_argument('dietary_restrictions',  type=strn)

    @auth
    def post(self, id):

        args = self.parser.parse_args()

        # find the most recent signup data for given user_id
        old_signup_data = SignupData.query.filter_by(user_id=id, outdated=False).scalar()

        if not old_signup_data:
            return {"status": "User does not exist"}, 400

        old_signup_data.outdated = True

        # create a copy, and overwrite the specified values
        data_copy = copy_row(SignupData, old_signup_data, ['id', 'outdated'])

        changed = False
        for k, v in args.items():
            if v and data_copy.__dict__[k] != v:
                data_copy.__setattr__(k, v)
                changed = True

        if changed:
            if old_signup_data != data_copy:
                # add the new data to the data tabe
                db.session.add(data_copy)
                db.session.commit()

                # add a new signup to the signup table
                signup = Signup(user_id=id, data_id=data_copy.id)
                db.session.add(signup)
                db.session.commit()

        # NV TODO: If email is changed, need to re-verify
        # NV TODO: if string is empty change to null, make sure to recheck age condition

        if changed:
            return {"status": "ok"}
        else:
            return {"status": "ok", "message": "unchanged"}

api.add_resource(SignupEndpoint, '/registration/v1/signup')
api.add_resource(ModifyEndpoint, '/registration/v1/modify/<id>')

