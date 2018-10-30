import os
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

# setup app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['LAH_EMAIL_LIST_DB'] # required

app.config['JWT_SECRET'] = os.environ.get('LAH_JWT_SECRET')
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('LAH_GOOGLE_CLIENT_ID')
app.config['GSUITE_DOMAIN_NAME'] = os.environ.get('LAH_GSUITE_DOMAIN_NAME')
app.config['DISABLE_AUTHENTICATION'] = os.environ.get('LAH_DISABLE_AUTHENTICATION')

# setup resp api and database
api = Api(app)
db = SQLAlchemy(app)

# load in the endpoints
import registration_2019.email_list
import registration_2019.authentication
import registration_2019.registration

# create db tables
db.create_all()
db.session.commit()
