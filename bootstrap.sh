#!/bin/bash
export FLASK_APP=./registration_2019/core.py
export LAH_GSUITE_DOMAIN_NAME="losaltoshacks.com"

if [ "$REG_DEBUG" = true ] ; then
    export FLASK_DEBUG=true
    export LAH_REGISTRATION_DB='sqlite:////tmp/registration_2019.db'
#    export LAH_REGISTRATION_DB='mysql+pymysql://<user>:<password>@<host>:<port>/<db-name>'
    export LAH_JWT_SECRET='foobar' # NOT SAFE (duh)
fi

source $(pipenv --venv)/bin/activate
flask run -h 0.0.0.0
