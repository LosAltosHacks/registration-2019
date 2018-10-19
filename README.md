# Registration Server 2019

A flask application with REST endpoints to

## Usage

Set `REG_DEBUG` to run flask in debug mode, and use a local database under `/tmp/registration_2019.db`

```shell
REG_DEBUG=true ./bootstrap
```

To deploy (not in debug mode), the following environment variables must be set:
- `LAH_EMAIL_LIST_DB`: DB URI (e.g. `mysql+pymysql://<user>:<password>@<host>:<port>/<db-name>`)
- `LAH_JWT_SECRET`: Secret for JWT authentication

## Endpoints

### Email List

`/email_list/subscribe` `POST`:

```json
{
    "email": "[255 chars max]"
}
```

`/email_list/unsubscribe` `POST`:

```json
{
    "email": "[255 chars max]",
    "token": "[36 chars]"
}
```
