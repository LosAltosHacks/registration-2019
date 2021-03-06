import os
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# setup app
app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}}) # provides 'Access-Control-Allow-Origin' header
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['LAH_REGISTRATION_DB'] # required

app.config['JWT_SECRET'] = os.environ.get('LAH_JWT_SECRET')
app.config['DOCUSIGN_AUTH'] = os.environ.get('LAH_DOCUSIGN_AUTH')
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('LAH_GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_ID_IOS'] = os.environ.get('LAH_GOOGLE_CLIENT_ID_IOS')
app.config['GSUITE_DOMAIN_NAME'] = os.environ.get('LAH_GSUITE_DOMAIN_NAME')
app.config['DISABLE_AUTHENTICATION'] = os.environ.get('LAH_DISABLE_AUTHENTICATION')
app.config['SES_AWS_REGION'] = os.environ.get('LAH_SES_AWS_REGION')
app.config['SES_SENDER'] = os.environ.get('LAH_SES_SENDER')
app.config['API_ENDPOINT'] = os.environ.get('LAH_API_ENDPOINT')
app.config['CONFIRMATION_REDIRECT'] = os.environ.get('LAH_CONFIRMATION_REDIRECT')

# setup resp api and database
api = Api(app)
db = SQLAlchemy(app)

# load in the endpoints
import registration_2019.email_list
import registration_2019.authentication
import registration_2019.registration
import registration_2019.mentor
import registration_2019.guest
import registration_2019.dayof
import registration_2019.discord
import registration_2019.docusign

# create db tables
db.create_all()
db.session.commit()
