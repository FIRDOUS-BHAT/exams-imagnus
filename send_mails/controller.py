import json
import pytz
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import email.utils
import os
import smtplib
from fastapi import FastAPI, APIRouter, BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from starlette.requests import Request
from starlette.responses import JSONResponse
from pydantic import EmailStr, BaseModel
from typing import List
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder
from send_mails.models import StudentEnquiry, StudentEnquiryIn_Pydantic
import smtplib
from email.message import EmailMessage
from functools import lru_cache
import threading

from configs import mailinfo


@lru_cache()
def app_setting():
    return mailinfo.Setting()


settings = app_setting()

tz = pytz.timezone('Asia/Kolkata')


class Envs:
    MAIL_USERNAME = settings.mail_username
    MAIL_PASSWORD = settings.mail_password
    MAIL_FROM = settings.mail_from
    MAIL_PORT = settings.mail_port
    MAIL_SERVER = settings.mail_server
    MAIL_FROM_NAME = settings.mail_from_name


app = FastAPI()
router = APIRouter()


class EmailSchema(BaseModel):
    email: List[EmailStr]


conf = ConnectionConfig(
    MAIL_USERNAME=Envs.MAIL_USERNAME,
    MAIL_PASSWORD=Envs.MAIL_PASSWORD,
    MAIL_FROM=Envs.MAIL_FROM,
    MAIL_PORT=Envs.MAIL_PORT,
    MAIL_SERVER=Envs.MAIL_SERVER,
    MAIL_FROM_NAME=Envs.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER='send_mails/templates/'
)



def send_email(recipient: str,email_content: str, ):
    msg = EmailMessage()
    msg.set_content(email_content)
    msg['Subject'] = 'Imagnus verification code'
    msg['From'] = settings.mail_from
    msg['To'] = recipient
   
    with smtplib.SMTP(settings.mail_server , 587) as server:
        server.starttls()
        server.login(settings.mail_username , settings.mail_password)
        server.send_message(msg)


async def send_email_in_background(recipient: str, email_content: str):
    # background_tasks.add_task(send_email, email_content, recipient)
    email_thread = threading.Thread(target=send_email, args=(recipient, email_content))
    email_thread.start()
    return True


@router.post("/send_mail")
async def send_mail(email: EmailSchema) -> JSONResponse:
    try:
        template = """
		<html>
		<body>

        <p>Hi !!!
                <br>Thanks for using fastapi mail, keep using it..!!!</p>

                </body>
                </html>
                """

        message = MessageSchema(
            subject="Fastapi-Mail module",
            # List of recipients, as many as you can pass
            recipients=email.dict().get("email"),
            template_body=email.dict().get("body"),
            subtype="html"
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name='email.html')
        print(message)

        return JSONResponse(status_code=200, content={"message": "email has been sent"})
    except Exception as ex:
        return {"detail": str(ex)}


async def send_email_async(subject: str, email_to: str, body: dict):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype='html',
    )

    fm = FastMail(conf)
    await fm.send_message(message, template_name='email.html')


@router.get('/send-email/asynchronous')
async def send_email_asynchronous():
    await send_email_async('Hello World', 'firdousbhat.ai@gmail.com',
                           {'title': 'Hello World', 'name': 'John Doe'})
    return 'Success'


async def send_email_background(background_tasks: BackgroundTasks, subject: str, email_to: str, body: dict):

    message = MessageSchema(
        subject=subject,
        recipients=[
            email_to,
            "invoice@imagnus.in" 
        ],
        template_body=body,
        subtype='html',
    )
    fm = FastMail(conf)
    background_tasks.add_task(
        fm.send_message, message, template_name='order.html'
    )


class EmailInputModel(BaseModel):
    name: str
    course: str
    payment_id: str
    order_id: str
    total_amount: int


@router.post('/send-email/backgroundtasks')
async def send_email_backgroundtasks(background_tasks: BackgroundTasks, email_to: str, body: EmailInputModel):
    try:
        total_amount = body.total_amount
        now = datetime.now(tz)
        created_at = now.strftime('%d %B, %Y')
        course_price = round((total_amount)/1.18, 2)
        gst = round(course_price*0.18, 2)
        body = jsonable_encoder(body)
        body.update({"course_price": course_price})
        body.update({"gst": gst})
        body.update({"total_amount": total_amount})
        body.update({"created_at": created_at})
        resp = await send_email_background(background_tasks, 'Invoice',
                                           email_to, body)
        return {"status": str(resp)}
    except Exception as ex:
        # return {"status": False, "message": "You've already submitted the request"}
        return {"detail": str(ex)}


@router.get('/send_ses_mails/')
async def send_ses_mails():

    # Replace sender@example.com with your "From" address.
    # This address must be verified.
    SENDER = 'no-reply@imagnus.in'
    SENDERNAME = 'Sender Name'

    # Replace recipient@example.com with a "To" address. If your account
    # is still in the sandbox, this address must be verified.
    RECIPIENT = 'frdsbhat9@gmail.com'

    # Replace smtp_username with your Amazon SES SMTP user name.
    USERNAME_SMTP = Envs.MAIL_USERNAME

    # Replace smtp_password with your Amazon SES SMTP password.
    PASSWORD_SMTP = Envs.MAIL_PASSWORD

    # (Optional) the name of a configuration set to use for this message.
    # If you comment out this line, you also need to remove or comment out
    # the "X-SES-CONFIGURATION-SET:" header below.
    #CONFIGURATION_SET = "ConfigSet"

    # If you're using Amazon SES in an AWS Region other than US West (Oregon),
    # replace email-smtp.us-west-2.amazonaws.com with the Amazon SES SMTP
    # endpoint in the appropriate region.
    HOST = "email-smtp.ap-south-1.amazonaws.com"
    PORT = 587

    # The subject line of the email.
    SUBJECT = 'Amazon SES Test (Python smtplib)'

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ("Amazon SES Test\r\n"
                 "This email was sent through the Amazon SES SMTP "
                 "Interface using the Python smtplib package."
                 )

    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
    <h1>Amazon SES SMTP Email Test</h1>
    <p>This email was sent with Amazon SES using the
        <a href='https://www.python.org/'>Python</a>
        <a href='https://docs.python.org/3/library/smtplib.html'>
        smtplib</a> library.</p>
    </body>
    </html>
                """

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = SUBJECT
    msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
    msg['To'] = RECIPIENT
    # Comment or delete the next line if you are not using a configuration set
    #msg.add_header('X-SES-CONFIGURATION-SET', CONFIGURATION_SET)

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(BODY_TEXT, 'plain')
    part2 = MIMEText(BODY_HTML, 'html')
    part3 = MIMEApplication(
        open('/home/firdous/Documents/Rafiya Showkat.pdf', 'rb').read())

    part3.add_header("Content-Disposition", 'attachment', filename='Resume')
    msg.attach(part3)
    # part3 = MIMEMultipart(
    #     '', 'image')
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    msg.attach(part3)
    import boto3
    import urllib.request

    from functools import lru_cache
    from botocore.client import Config
    from configs import appinfo

    @lru_cache()
    def app_setting():
        return appinfo.Setting()

    settings = app_setting()

    aws_access_key_id = settings.AWS_SERVER_PUBLIC_KEY
    aws_secret_access_key = settings.AWS_SERVER_SECRET_KEY
    aws_region = settings.AWS_SERVER_REGION

    s3Client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        config=Config(signature_version='s3v4'),
        region_name=aws_region,
    )

    # Attach files from S3

    myurl = "https://ik.imagekit.io/imagnus/Notes/eaa1467e-3e01-423b-9bcd-36d7b2cdbe5e/21ce3837-f78b-4bc0-9266-c4098fd23e4a/5badc3df-24cc-4a67-af78-c5cb5157e301/Ease of Doing Business (व्यवसायगत सरलता)/Ease of doing business.pdf"

    s3_object = s3Client.get_object(ClientMethod='get_object',
                                    Params={
                                        'Bucket': 'testing-bucket-s3-uploader',
                                        'Key': 'material_url_key'
                                    },)
    body = s3_object['Body'].read()

    part = MIMEApplication(body, 'filename')
    part.add_header("Content-Disposition", 'attachment', filename='filename')
    msg.attach(part)

    # Try to send the message.
    try:
        server = smtplib.SMTP(HOST, PORT)
        server.ehlo()
        server.starttls()
        # stmplib docs recommend calling ehlo() before & after starttls()
        server.ehlo()
        server.login(USERNAME_SMTP, PASSWORD_SMTP)
        server.sendmail(SENDER, RECIPIENT, msg.as_bytes())
        server.close()
        print("Email sent!")
    # Display an error message if something goes wrong.
    except Exception as e:
        print("Error: ", e)

    return {"email sent"}
