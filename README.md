# Registration Server 2019

A flask application with REST endpoints for the 2019 registration backend

## Usage

First make sure `pipenv` is installed

Set `REG_DEBUG` to run flask in debug mode (uses a local database under `/tmp/registration_2019.db`):

```shell
REG_DEBUG=true ./bootstrap
```

To disable authentication (for testing purposes), the environment variable `LAH_DISABLE_AUTHENTICATION` can also be set:

```shell
LAH_DISABLE_AUTHENTICATION=true REG_DEBUG=true ./bootstrap
```

If authentication is disabled, the JWT still must be provided however it is not used, so the header can just contain an arbitrary string

To deploy (not in debug mode), the following environment variables must be set:
- `LAH_REGISTRATION_DB`: DB URI (e.g. `mysql+pymysql://<user>:<password>@<host>:<port>/<db-name>`)
- `LAH_JWT_SECRET`: Secret for JWT authentication
- `LAH_GOOGLE_CLIENT_ID`: Client ID for google oauth
- `LAH_API_ENDPOINT`: The URI of the API endpoint to use when sending verification emails
- `AWS_ACCESS_KEY_ID`: Amazon access key to send emails through SES
- `AWS_SECRET_ACCESS_KEY`: Amazon secret key to send emails through SES

```shell
LAH_REGISTRATION_DB="..." LAH_JWT_SECRET="*******" LAH_GOOGLE_CLIENT_ID="<...>.apps.googleusercontent.com" ./bootstrap.sh
```

## Endpoints

Note that any endpoint with JWT authentication must contain the token in the header as a Bearer token

To authenticate from `curl`, simple add the following:
```bash
-H "Authorization: Bearer <token>"
```

### OAuth

#### `/oauth/v1/login` `POST`

Request body:
```js
{
    "token": "[string]"
}
```

Verifies a login through oauth with Google

Response:
- `401`: `{"message": "Could not authenticate"}`
- `200`: `{"jwt": "..."}`

On `200` response, the `"jwt"` should be stored and provided upon further requests

Note that the JWT will expire after 1 day of its creation

### Email List

#### `/email_list/v1/subscribe` `POST`

Request body:
```js
{
    "email": "[string]"
}
```

Response will be among:
- `200`: `{"status": "ok"}`
- `400`: `{"message": {...}}` (detailed `reqparse` error if parameters are incorrect)


#### `/email_list/v1/subscriptions` `GET` (JWT authenticated)

Returns a list of emails on the email list:
`200`: `["test@example.com", "test2@example.com", ...]`

### Registration

#### `/registration/v1/signup` `POST`

Request body:
```js
{
    # required:
    "first_name": "...",
    "surname": "...",
    "email": "name@example.com",
    "age": 18,
    "school": "...",
    "grade": 12,
    "student_phone_number": "5555555555"
    "gender": "...",
    "ethnicity": "..."
    "tshirt_size": "S", # can be "S", "M", "L", or "XL"
    "previous_hackathons": 0,

    # required if age is under 18:
    "guardian_name": "...",
    "guardian_email": "...",
    "guardian_phone_number": "5555555555",

    # optional:
    "github_username": "...",
    "linkedin_profile": "...",
    "dietary_restrictions": "..."
}
```

Responses will be among the following:
- `200`: `{"status": "ok"}`
- `400`: `{"message": "Minors must provide guardian information"}`
- `400`: `{"message": {...}}` (detailed `reqparse` error if parameters are incorrect)

When implementing a frontend that calls this endpoint, it is recommended to preprocess some data, e.g.:
- Sanitize phone numbers from (XXX) XXX-XXXX or XXX.XXX.XXXX, etc to XXXXXXXXXX (for ease of searching), and display them back in a consistent (more readable) format
- Verify the format of emails
- If applicant is under 18 years old, ensure that guardian info is inputted (maybe even hide said fields if age is 18+)
- Provide male and female options for gender, along with an "other" field for custom inputs
- Provide a list of common dietary restrictions as checkboxes (vegetarian, vegan, peanut allergy, etc) as well as an "other" for custom input

Note that these recommendations are not necessarily enforced on the server level, but they will help maintain some consistency in the database


#### `/registration/v1/verify/<user_id>/<email_token>/` `GET`

Will attempt to verify the user's email

Responses will be among the following:
- `422`: `{"message": "Could not verify"}`
- `200`: `{"status": "ok"}`

#### `/registration/v1/modify/<user_id>` `POST` (JWT authenticated)

Request body:
Same as to `signup` endpoint, except:
- all fields are optional
- can also accept `"acceptance_status"` field, with possible values:
  - `"none"`
  - `"waitlisted"`
  - `"rejected"`
  - `"queue"`
  - `"accepted"`
- can also accept `"email_verified"` field, with a boolean value

Will update the user's data with the changes provided in the request

Response will be among:
- `200`: `{"status": "ok"}`
- `200`: `{"status": "ok", "message": "unchanged"}`
- `400`: `{"message": "Minors must provide guardian information"}`
- `400`: `{"message": "Email already in use"}`
- `400`: `{"message": {...}}` (detailed `reqparse` error if parameters are incorrect)

#### `/registration/v1/list` `GET` (JWT authenticated)

Lists all signups (only the most recent and up-to-date data, where `outdated=False`)

Response will be a list of JSON objects, each corresponding to a signup:

```js
[
    {
        "user_id": "f12e9cb1-25a4-4ebc-bcaf-0d79a7f95a9f",
        "first_name": "FirstName",
        "surname": "LastName",
        "email": "foo2@gmail.com",
        "age": 18,
        "school": "SomeSchool",
        "grade": 12,
        "student_phone_number": "555-555-5555",
        "gender": "male",
        "ethnicity": "Ethnicity",
        "tshirt_size": "L",
        "previous_hackathons": 0,
        "guardian_name": "",
        "guardian_email": "",
        "guardian_phone_number": "555-555-5555",
        "github_username": null,
        "linkedin_profile": null,
        "dietary_restrictions": null,
        "signed_waver": false,
        "acceptance_status": "none",
        "email_verified": true,
        "timestamp": "2018-10-30 03:23:32",
        "outdated": false
    }, ...
]
```

#### `/registration/v1/search` `POST` (JWT Authenticated)

Request body should be a JSON object with a single key `"query"`

The query can be a string, in which case it is checked against each of the following conditions:
- `user_id` equals query
- `first_name` contains query
- `surname` contains query
- `email` contains query
- `student_phone_number` contains query
- `guardian_name` contains query
- `guardian_email` contains query
- `guardian_phone_number` contains query

The query can also be a JSON object, accepting (optionally) each of the fields returned in the `list` endpoint, except for `timestamp`

If `outdated` is provided in the request, it will also be provided in the response (otherwise it will be assumed false and omitted)

`outdated` can also have a value of `*`, in which case both current and outdated signups will be returns

#### `/registration/v1/history/<user_id>` `GET` (JWT Authenticated)

Gets the history (all `outdated=True` and `outdated=False` signups) for a user

Note that after a user is deleted (using the `delete` endpoint), history will still find the data given user_id

Response will be among:
- `400`, `{"message": "User does not exist"}`
- `200`, `[{}, ...]` (list of signups with same format as the `list` and `search` endpoints, and the `outdated` field)

#### `/registration/v1/delete/<user_id>` `GET` (JWT Authenticated)

Deletes the user from the database (internally just sets `outdated` to true for all of the user's signups)

Response will be among:
- `400`, `{"message": "User does not exist"}`
- `200`, `{"status": "ok"}`

### Chaperone

#### `/chaperone/v1/signup` `POST` (JWT authenticated)

Request body:
```js
{
    # required:
    "name": "...",
    "email": "name@example.com",

    # optional:
    "phone": "..."
}
```

Responses will be among the following:
- `200`: `{"status": "ok"}`
- `200`: `{"status": "ok", "message": "chaperone already added (by email)"}`
- `400`: `{"message": {...}}` (detailed `reqparse` error if parameters are incorrect)

#### `/chaperone/v1/modify/<chaperone_id>` `POST` (JWT authenticated)

Request body:
Same as to chaperone `signup` endpoint, except all fields are optional

Response will be among:
- `200`: `{"status": "ok"}`
- `200`: `{"status": "ok", "message": "unchanged"}`
- `400`: `{"message": "Email already in use"}`
- `400`: `{"message": {...}}` (detailed `reqparse` error if parameters are incorrect)

#### `/chaperone/v1/list` `GET` (JWT authenticated)

Lists all chaperones (only the most recent and up-to-date data, where `outdated=True`)

Response will be a list of JSON objects, each corresponding to a chaperone

#### `/registration/v1/search` `POST` (JWT Authenticated)

Request body should be a JSON object with a single key `"query"`

The query can be a string, in which case it is checked against each of the following conditions:
- `chaperone_id` equals query
- `name` contains query
- `email` contains query
- `phone` contains query

The query can also be a JSON object, accepting (optionally) each of the fields returned in the chaperone `list` endpoint, except for `timestamp`

If `outdated` is provided in the request, it will also be provided in the response (otherwise it will be assumed false and omitted)

`outdated` can also have a value of `*`, in which case both current and outdated signups will be returns

#### `/chaperone/v1/delete/<chaperone_id>` `GET` (JWT Authenticated)

Deletes the user from the database (internally just sets `outdated` to true for all of the user's signups)

Response will be among:
- `400`, `{"message": "Chaperone does not exist"}`
- `200`, `{"status": "ok"}`
