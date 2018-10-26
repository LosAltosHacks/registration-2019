# Registration Server 2019

A flask application with REST endpoints for the 2019 registration backend

## Usage

First make sure `pipenv` is installed

Set `REG_DEBUG` to run flask in debug mode (uses a local database under `/tmp/registration_2019.db`)

```shell
REG_DEBUG=true ./bootstrap
```

To deploy (not in debug mode), the following environment variables must be set:
- `LAH_EMAIL_LIST_DB`: DB URI (e.g. `mysql+pymysql://<user>:<password>@<host>:<port>/<db-name>`)
- `LAH_JWT_SECRET`: Secret for JWT authentication

## Endpoints

Note that any endpoint with JWT authentication must contain the token in the header as a Bearer token

To authenticate from `curl`, simple add the following:
```bash
-H "Authorization: Bearer <token>"
```

### OAuth

`/oauth/v1/login` `POST`:

```json
{
    "code": "[string]"
}
```

Verifies a login through oauth with Google

Returns a JWT to be provided in further requests

### Email List

`/email_list/v1/subscribe` `POST`:

```json
{
    "email": "[string]"
}
```

`/email_list/v1/subscriptions` `GET` (JWT authenticated):

Returns a JSON list of emails on the email list

### Registration

NV TODO: Finish adding to this doc from https://docs.google.com/document/d/1Jqaw5uFl18QguDwOoZJOYnERD5Rx57R9DD5r4Clh4KE
