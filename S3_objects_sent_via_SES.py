import boto3
from datetime import datetime
from os import environ
from email import encoders
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def lambda_handler(event, context):

    #Object and bucket names are taken from the PUT
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_name = event['Records'][0]['s3']['object']['key']

    def save_in_dynamo():
        #S3 object URI
        s3_uri = 's3://' + bucket_name + '/' + object_name

        #Record the time in which the object is put in the S3 bucket
        now = datetime.now()
        creation_time = now.strftime('%Y-%m-%d, %H:%M:%S')

        #Put objects are saved in a DynamoDB table along with the S3 object URI and creation time. This can help track when objects were put in the S3 buckets and emails were sent.
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('S3_objects_sent_via_SES') 
        table.put_item(Item={
                'Object_name': object_name,
                'Creation_time': creation_time,
                'S3_URI': s3_uri
            })
    
    def send_email_with_file():
    
        #Email message is sent via SES with file attached to it.
    
        #Download file from S3
        s3Resource = boto3.resource('s3')
        s3Resource.Object(bucket_name, object_name).download_file('/tmp/' + object_name)
        filename = '/tmp/' + object_name

        #Email parameters
        msg = MIMEMultipart()
        msg["Subject"] = environ['subject']
        msg["From"] = environ['from']
        msg["To"] = environ['to']

        # Set message body
        body = MIMEText(environ['bodytext'], "plain")
        msg.attach(body)

        with open(filename, "rb") as attachment:
            part = MIMEApplication(attachment.read())
            part.add_header("Content-Disposition",
                            "attachment",
                            filename=filename)
        msg.attach(part)

        # Convert message to string and send
        ses_client = boto3.client("ses", region_name="us-east-1")
        response = ses_client.send_raw_email(
            #Optional parameters, read Boto3 documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ses.html#SES.Client.send_raw_email
            #Source=environ['from']
            #Destinations=[environ['to']],
            RawMessage={"Data": msg.as_string()}
            )
    
    #Executes function to add entries to a DynamoDB table. Comment the line below if you do not want to track objects with DynamoDB.
    save_in_dynamo()

    #Sends email with file attached to it
    send_email_with_file()
