import boto3
from botocore.exceptions import ClientError
from .core import app

CONFIRMATION_SUBJECT = "Los Altos Hacks Registration Confirmation"

CONFIRMATION_TEXT = ("You have registered!"
                     "Please click here to verify your email")

# TODO: Add in actual email templates, and make sure navigating to whatever url will verify the email
CONFIRMATION_HTML = """<html>
<head></head>
<body>
  <h1>You have registered!</h1>
  <p>Please click <a href='https://losaltoshacks.com/verify'>here</a> to verify your email</p>
</body>
</html>"""


client = boto3.client('ses', region_name=app.config['SES_AWS_REGION'])

def send_confirmation_email(to, email_verification_token):
    try:
        response = client.send_email(
            Destination={
                'ToAddresses': [to]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': CONFIRMATION_HTML
                    },
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': CONFIRMATION_TEXT
                    }
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': CONFIRMATION_SUBJECT
                }
            },
            Source = app.config['SES_SENDER'])
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Sent email to " + to + "; MessageId: '" + response['MessageId'] + "'")

def send_reregistered_email(to):
    # TODO: Send email like "Did you try to register again with different information? Please contact our team at <email> if you'd like to change the data you provided". If their email is verified, also send the new data so they can forward to us to change, and change the message to "...different information? Please forward this email to <email> if you'd like to change the data you provided"
    print('unimplemented')
