import os
import ConfigParser

import boto3

from chalice import Chalice
from chalice import ForbiddenError, BadRequestError

app = Chalice(app_name='email-forwarder')
# app.debug = True

SUBJECT = 'Message from %s'

config = ConfigParser.SafeConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'chalicelib', 'config.ini'))

allowed_domains = config.get('DEFAULT', 'domains').split(',')
to_addresses = config.get('DEFAULT', 'to_addresses').split(',')
from_address = config.get('DEFAULT', 'from_address')


@app.route('/', methods=['POST'], cors=True)
def forward_email():
    # This is the JSON body the user sent in their POST request.
    json_body = app.current_request.json_body

    sender_name = json_body['sender_name'].strip() if 'sender_name' in json_body else None
    sender_email = json_body['sender_email'].strip() if 'sender_email' in json_body else None
    body = json_body['body'].strip() if 'body' in json_body else None
    domain = json_body['domain'].strip() if 'domain' in json_body else None

    if not domain in allowed_domains:
        raise ForbiddenError("Invalid domain")

    if not body or len(body) == 0:
        raise BadRequestError('Missing body')

    updated_body = """
Domain: %s
From: %s
Email: %s
Message:

%s
""" % (domain, sender_name, sender_email, body)

    if sender_email:
        reply_to = ["%s <%s>" % (sender_name, sender_email) if sender_name
                    else sender_email]
    else:
        reply_to = []

    client = boto3.client('ses')

    response = client.send_email(
        Source=from_address,
        Destination={
            'ToAddresses': to_addresses
        },
        Message={
            'Subject': {
                'Data': SUBJECT % domain,
                'Charset': 'utf8'
            },
            'Body': {
                'Text': {
                    'Data': updated_body,
                    'Charset': 'utf8'
                }
            }
        },
        # **reply_to
        ReplyToAddresses=reply_to,
    )

    return {'status': 'OK' if 'MessageId' in response else 'ERROR'}
