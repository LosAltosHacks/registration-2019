#!/bin/bash
export FLASK_APP=./registration_2019/core.py
export LAH_GSUITE_DOMAIN_NAME="losaltoshacks.com"
export LAH_SES_AWS_REGION="us-west-2"
export LAH_SES_SENDER="Los Altos Hacks <info@losaltoshacks.com>"
export LAH_CONFIRMATION_REDIRECT="https://www.losaltoshacks.com/confirm.html"

if [ "$REG_DEBUG" = true ] ; then
    export FLASK_DEBUG=true
    export LAH_REGISTRATION_DB='sqlite:////tmp/registration_2019.db'
#    export LAH_REGISTRATION_DB='mysql+pymysql://<user>:<password>@<host>:<port>/<db-name>'
    export LAH_JWT_SECRET='foobar' # NOT SAFE (duh)
    export LAH_API_ENDPOINT='http://localhost:5000'
fi

source $(pipenv --venv)/bin/activate
flask run -h 0.0.0.0
