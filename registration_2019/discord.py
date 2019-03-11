from flask_restful import Resource, reqparse
from .core import api, db, app
from .helper import *
from .authentication import auth
from .guest import Guest
from .mentor import Mentor
from .registration import Signup, AcceptanceStatusEnum

## Helpers

def get_info_from_email(email):
    # Search through all attendees to find one with the right email
    # Priority order is mentor, guest-types, attendee
    mentor = Mentor.query.filter_by(email=email, outdated=False).scalar()
    if mentor:
        if not mentor.email_verification.verified:
            return {'message': 'Email not verified'}, 400
        return {
            'role': 'mentor',
            'name': mentor.name,
        }, 200

    guest = Guest.query.filter_by(email=email, outdated=False).scalar()
    if guest:
        return {
            'role': guest.kind.value,
            'name': guest.name,
        }, 200

    attendee = Signup.query.filter_by(email=email, outdated=False).scalar()
    if attendee:
        if not attendee.email_verification.verified:
            return {'message': 'Email not verified'}, 400
        if attendee.acceptance_status.value not in ("accepted", "whitelisted"):
            return {'message': 'Not accepted', 'current_status': attendee.acceptance_status.value}, 400
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

api.add_resource(DiscordVerifyEndpoint, '/discord/v1/discord-verify')
