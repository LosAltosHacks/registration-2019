import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['LAH_EMAIL_LIST_DB']
app.config['JWT_SECRET'] = os.environ['LAH_JWT_SECRET']

db = SQLAlchemy(app)

# load in the endpoints

import registration_2019.email_list
# import ...

# create the DB tables after all the endpoints have defined their models

db.create_all()
db.session.commit()
