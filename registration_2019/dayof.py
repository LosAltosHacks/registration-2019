import datetime
import enum
from sqlalchemy import Column, String, SmallInteger, Integer, Enum, Boolean, ForeignKey, DateTime
from flask import redirect
from flask_restful import Resource, reqparse
from .core import api, db, app
from .helper import *
from .authentication import auth
from .registration import Signup
from .mentor import Mentor
from .guest import Guest
from .dayof_model import SignIn

# TODO write actual regex
badge_data = re_matches(".*", "badge data")

def sign_in(user_id, badge_data):
    if SignIn.query.filter_by(badge_data=badge_data).scalar():
        return {"messge": "badge_data already in use"}, 400

    signup = Signup.query.filter_by(user_id=user_id, outdated=False).scalar()
    if signup:
        if signup.sign_in:
            return {"message": "User already signed in"}, 400
        sign_in = SignIn(badge_data=badge_data)
        db.session.add(sign_in)
        signup.sign_in = sign_in
        db.session.commit()
        return {"status": "ok"}

    mentor = Mentor.query.filter_by(mentor_id=user_id, outdated=False).scalar()
    if mentor:
        if mentor.sign_in:
            return {"message": "User already signed in"}, 400
        sign_in = SignIn(badge_data=badge_data)
        db.session.add(sign_in)
        mentor.sign_in = sign_in
        db.session.commit()
        return {"status": "ok"}

    guest = Guest.query.filter_by(guest_id=user_id, outdated=False).scalar()
    if guest:
        if guest.sign_in:
            return {"message": "User already signed in"}, 400
        sign_in = SignIn(badge_data=badge_data)
        db.session.add(sign_in)
        guest.sign_in = sign_in
        db.session.commit()
        return {"status": "ok"}

    return {"message": "User ID not found"}, 400

def sign_out(badge_data):
    sign_in = SignIn.query.filter_by(badge_data=badge_data).scalar()
    if not sign_in:
        return {"message": "Invalid badge"}, 400
    if sign_in.signed_out:
        return {"message": "User already signed out"}, 400
    sign_in.signed_out = True
    db.session.commit()
    return {"status": "ok"}

def meal_line(args):
    if args["meal_number"] > 9 or args["meal_number"] < 1:
        return {"message": "Invalid meal number"}, 400
    sign_in = SignIn.query.filter_by(badge_data=args.get("badge_data")).scalar()
    if not sign_in:
        return {"message": "Invalid badge"}, 400
    meal_name = "meal_" + str(args["meal_number"])
    times = getattr(sign_in, meal_name)
    if times >= args["allowed_servings"]:
        return {"message": "User has already received allowed servings for this meal"}, 400
    setattr(sign_in, meal_name, times+1)
    db.session.commit()
    return {"status": "ok", "message": "Servings received incremented"}


## Endpoints

class SignInEndpoint(Resource):

    parser = reqparse.RequestParser()

    def __init__(self):

        self.parser.add_argument('user_id',            type=strn, required=True)
        self.parser.add_argument('badge_data',         type=badge_data, required=True)

    @auth
    def post(self):
        args = self.parser.parse_args()
        return sign_in(args['user_id'], args['badge_data'])

    @auth
    def get(self):
        return {
            'attendee': Signup.query.filter(Signup.sign_in_id.isnot(None), Signup.outdated == False).count(),
            'mentor': Mentor.query.filter(Mentor.sign_in_id.isnot(None), Mentor.outdated == False).count(),
            'guest': Guest.query.filter(Guest.sign_in_id.isnot(None), Guest.outdated == False).count(),
        }


class MealLine(Resource):
    parser = reqparse.RequestParser()

    def __init__(self):
        self.parser.add_argument('badge_data',         type=badge_data, required=True)
        self.parser.add_argument('meal_number',        type=int,  required=True)
        self.parser.add_argument('allowed_servings',   type=int,  required=True)

    @auth
    def post(self):
        args = self.parser.parse_args()
        return meal_line(args)

api.add_resource(SignInEndpoint,  '/dayof/v1/sign-in')
api.add_resource(MealLine,        '/dayof/v1/meal')
