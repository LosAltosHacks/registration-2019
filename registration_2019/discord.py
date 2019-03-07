from flask_restful import Resource, reqparse
from .core import api, db, app
from .helper import *
from .authentication import auth
from .chaperone import Chaperone
from .mentor import Mentor
from .registration import Signup

## Helpers

def get_info_from_email(email):
    # Search through all attendees to find one with the right email
    # Priority order is mentor, chaperone-types, attendee
    mentor = Mentor.query.filter_by(email=email, outdated=False).scalar()
    if mentor:
        if not mentor.email_verification.verified:
            return {'message': 'Email not verified'}, 400
        return {
            'role': 'mentor',
            'name': mentor.name,
        }, 200

    chaperone = Chaperone.query.filter_by(email=email, outdated=False).scalar()
    if chaperone:
        return {
            'role': chaperone.kind,
            'name': chaperone.name,
        }, 200

    attendee = Signup.query.filter_by(email=email, outdated=False).scalar()
    if attendee:
        if not attendee.email_verification.verified:
            return {'message': 'Email not verified'}, 400
        return {
            'role': 'attendee',
            'name': attendee.first_name + ' ' + attendee.surname,
        }, 200

    return {'message': 'Email not found in database'}, 400


## Endpoints
class DiscordVerifyEndpoint(Resource):
    parser = reqparse.RequestParser()

    def __init__(self):
        self.parser.add_argument('email',         type=email_string, required=True)

    @auth
    def post(self):
        args = self.parser.parse_args()
        return get_info_from_email(args['email'])

api.add_resource(DiscordVerifyEndpoint,  '/registration/v1/discord-verify')
