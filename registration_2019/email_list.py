import os
import uuid
from .core import app, db
from flask import jsonify, request
from flask_sqlalchemy import SQLAlchemy

def rand_uuid():
    return str(uuid.uuid4())

class EmailSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    token = db.Column(db.String(36), unique=True, nullable=False, default=rand_uuid)
    subscribed = db.Column(db.Boolean(), default=True)

def find_sub(search_email):
    return EmailSubscription.query.filter_by(email=search_email).first()

@app.route('/email_list/v1/subscribe', methods=['POST'])
def subscribe():
    req_email = request.get_json().get('email')

    sub = find_sub(req_email)

    if sub == None:
        sub = EmailSubscription(email=req_email)
        db.session.add(sub)
        db.session.commit()
    else:
        sub.subscribed = True
        db.session.commit()
    return jsonify({"status": "ok"}), 200

@app.route('/email_list/v1/unsubscribe', methods=['POST'])
def unsubscribe():
    json = request.get_json()
    req_email = json.get('email')
    req_token = json.get('token')

    sub = find_sub(req_email)

    if sub != None and sub.token == req_token:
        # email and correct token provided
        sub.subscribed = False
        db.session.commit()
        return jsonify({"status": "ok"}), 200
    elif sub != None:
        # incorrect token provided
        return jsonify({"message": "invalid token"}), 401
    else:
        # email not subscribed
        return jsonify({"status": "ok"}), 200



# TODO: Needs authentication
#@app.route('/email_list/v1/subscriptions', methods=['GET'])
#def subscriptions():
#    subscribed = EmailSubscription.query.filter_by(subscribed=True).all()
#    emails = list(map(lambda sub : sub.email, subscribed))
#    return jsonify(emails)
