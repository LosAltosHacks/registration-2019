import os
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

# setup app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['LAH_EMAIL_LIST_DB']
app.config['JWT_SECRET'] = os.environ['LAH_JWT_SECRET']

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
