#!/usr/bin/env python

import urllib.request
import urllib.parse
from fastapi import APIRouter, Depends
import json

from utils.util import get_current_user

router = APIRouter()

# import library
import math, random


# function to generate OTP
async def generateOTP():
    # Declare a digits variable
    # which stores all digits
    digits = "0123456789"
    OTP = ""

    # length of password can be chaged
    # by changing value in range
    for i in range(6):
        OTP += digits[math.floor(random.random() * 10)]

    return OTP


async def sendSMS(apikey, numbers, sender, message):
    try:
        data = urllib.parse.urlencode({'apikey': apikey, 'numbers': numbers,
                                       'message': message, 'sender': sender})
        data = data.encode('utf-8')
        request = urllib.request.Request("https://api.textlocal.in/send/?")
        f = urllib.request.urlopen(request, data)
        fr = f.read()
        return fr
    except:
        return {"An error occured"}


@router.post('/send_otp/')
async def send_otp(mobile: str, _=Depends(get_current_user)):
    otp = await generateOTP()
    # message = otp + " is your verification code for registration at i-Magnus."
    message = otp + " is your one time verification code for registration at i-Magnus."
    resp = await sendSMS('ODg1YjEyMDg5YWVkNGI3MGY5ZDhhODA4ZDMxNzIwNWQ=', '91' + mobile,
                         'IMGNUS', message)
    resp = json.loads(resp)
    if resp['status'] == 'success':
        print('OTP SENT TO '+mobile)
        res = {
            "status": resp['status'],
            "otp": otp

        }

    else:
        res = {
            "status": resp['status']
        }

    return res
