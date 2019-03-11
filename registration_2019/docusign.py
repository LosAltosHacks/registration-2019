import xml.etree.ElementTree as ET
import base64

from flask_restful import Resource, reqparse, abort
from flask         import request
from .core         import app, api, db
from .helper       import re_matches
from .registration import Signup
from .mentor       import Mentor
from .guest        import Guest

# @basic_auth decorator

auth_str = re_matches("Basic ([0-9a-zA-Z-]+)$", "authentication token", 1)

auth_parser = reqparse.RequestParser()
auth_parser.add_argument('authorization', type=auth_str, required=True, location='headers')

def is_authenticated(auth):
  try:
      decoded = base64.b64decode(auth).decode("utf-8")
  except:
    return False

  return decoded == app.config.get('DOCUSIGN_AUTH')

def basic_auth(f):
  def wrapper(*args, **kwargs):
      auth = auth_parser.parse_args()['authorization']

      if not app.config.get('DISABLE_AUTHENTICATION') and not is_authenticated(auth):
          abort(401, description="Not authenticated")

      return f(*args, **kwargs)

  return wrapper

def sign_attendee(email, parent_email):
    attendee = Signup.query.filter_by(email=email, outdated=False).scalar()

    if attendee and (attendee.age >= 18 or parent_email):
        attendee.signed_waiver = True
        db.session.commit()

def sign_mentor(email, parent_email):
    mentor = Mentor.query.filter_by(email=email, outdated=False).scalar()

    if mentor and (mentor.over_18 or parent_email):
        mentor.signed_waiver = True
        db.session.commit()

def sign_guest(email):
    guest = Guest.query.filter_by(email=email, outdated=False).scalar()

    if guest:
        guest.signed_waiver = True
        db.session.commit()

XML_NAMESPACES = {'ds': 'http://www.docusign.net/API/3.0'}

class DocusignEndpoint(Resource):

    def __init__(self):
        pass

    @basic_auth
    def post(self):
        data = request.get_data().decode("utf-8")

        email = None
        parent_email = None

        try:
            xml_root = ET.fromstring(data)

            if xml_root.tag != "{http://www.docusign.net/API/3.0}DocuSignEnvelopeInformation":
                return {'message': 'bad xml'}, 400

            email_elem = xml_root.findall('./ds:EnvelopeStatus/ds:RecipientStatuses/ds:RecipientStatus/ds:Email', XML_NAMESPACES)
            if len(email_elem) == 1:
                email = email_elem[0].text
                parent_email = None
            elif len(email_elem) == 2:
                email = email_elem[0].text
                parent_email = email_elem[1].text
            else:
                return {'message': 'bad xml'}, 400
        except Exception as e:
            return {'message': 'bad xml'}, 400

        # set all matching signups to signed
        sign_attendee(email, parent_email)

        sign_mentor(email, parent_email)

        sign_guest(email)

        return {"status": "ok"}

api.add_resource(DocusignEndpoint, '/waiver/v1/sign')
