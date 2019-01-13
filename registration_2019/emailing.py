import boto3
from botocore.exceptions import ClientError
from .core import app
from .helper import read_file

def read_email(name):
    prefix = f'email_templates/{name}/'
    return read_file(prefix + "subject"), read_file(prefix + "header_1"), read_file(prefix + "header_2"), read_file(prefix + "body"), read_file(prefix + "text")

def read_templates(*templates):
    temps = {}
    for t in templates:
        subject, header_1, header_2, body, text = read_email(t)
        temps[t] = {}
        temps[t]['subject'] = subject
        temps[t]['header_1'] = header_1
        temps[t]['header_2'] = header_2
        temps[t]['body'] = body
        temps[t]['text'] = text
    return temps

HTML_TEMPLATE = read_file('email_templates/html')

TEMPLATES = read_templates("confirmation", "mentor_confirmation")

def format_email(template, data):
    text = TEMPLATES[template]['text'].format(**data)
    subject = TEMPLATES[template]['subject'].format(**data)
    header_1 = TEMPLATES[template]['header_1'].format(**data)
    header_2 = TEMPLATES[template]['header_2'].format(**data)
    body = TEMPLATES[template]['body'].format(**data)

    message = {**data, 'header_1': header_1, 'header_2': header_2, 'body': body}
    return subject, text, HTML_TEMPLATE.format(**message)

client = boto3.client('ses', region_name=app.config['SES_AWS_REGION'])

def send_email_template(data, template):
    data['api_endpoint'] = app.config['API_ENDPOINT']
    try:
        subject, text, html = format_email(template, data)
        response = client.send_email(
            Destination = {'ToAddresses': [data['email']]},
            Message = {
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': html
                    },
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': text
                    }
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': subject
                }
            },
            Source = app.config['SES_SENDER'])
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Sent email to " + data['email'] + "; MessageId: '" + response['MessageId'] + "'")
