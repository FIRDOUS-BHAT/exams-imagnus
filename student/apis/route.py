

import aiohttp
from tortoise.expressions import Q
import uvicorn
from playsound import playsound
import os
from tqdm import tqdm
import subprocess
import numpy as np
from slugify import slugify
import json
import rich.progress
import requests
import httpx
from fastapi.responses import FileResponse
import http.client
import sys
import tempfile
import botocore.vendored.requests.packages.urllib3 as urllib3
import boto3
from FCM.route import push_service
from email_validator import validate_email, EmailNotValidError
from fastapi_cache.decorator import cache
import uuid
from datetime import datetime
from typing import List, Optional

import pytz
from botocore.client import BaseClient
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from starlette.config import Config
# from courses.models import PreferenceSchema, PreferenceDB, CourseBase
from starlette.responses import JSONResponse

from admin_dashboard.apis.pydantic_models import CourseCategoryTestSeriesOut
from admin_dashboard.controller import upload_images
from admin_dashboard.models import Coupons, Course, Category, CourseCategoryLectures, CourseCategoryNotes, \
    CourseCategoryTestSeries_Pydantic, CourseCategoryTestSeries, CourseSubscriptionPlans, \
    CourseCategoryLectures_Pydantic, CourseCategories, SubscriptionPlans, CourseCategoryTestSeriesQuestions
from aws_services.deps import s3_auth
from checkout.models import PaymentRecords, PaymentRecords_Pydantic
from configs import appinfo
from student.apis.pydantic_models import StudentVideoActivityPydanticIn, ActivityPydantic, \
    StudentNotesActivityPydanticIn, StudentTestSeriesActivityIn, GetBookmarksPydantic, RecommendedLecturesPydantic, \
    loginResponsePydantic, queryPydantic, studentPydantic
from student.models import Student, StudentCoursePreferences, StudentTestSeriesRecord, Student_Pydantic, StudentIn_Pydantic, Token, UsedCoupons, \
    UserIn
from student_choices.models import StudentChoices, studentVideoActivity, \
    studentNotesActivity, studentTestSeriesActivity, studentActivity, BookMarkedVideos, activeSubscription, \
    BookMarkedNotes, BookMarkedTestseries, Ask, ask_Pydantic, studentActivity_Pydantic, BookMarkedVideos_Pydantic, \
    BookMarkedNotes_Pydantic, BookMarkedTestseries_Pydantic
from utils import util
from utils.util import get_current_user
from functools import lru_cache

tz = pytz.timezone('Asia/Kolkata')

updated_at = datetime.now(tz)

config = Config(".env")
router = APIRouter()


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()

cache_time = settings.cache_time


class Status(BaseModel):
    message: str


@router.post('/auth/token/old', response_model=Token)
def generate_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "REDACTED_LEGACY_API_USERNAME" or form_data.password != "REDACTED_LEGACY_API_PASSWORD":
        raise HTTPException(status_code=208, detail="Bad username or password")

    # subject identifier for who this token is for example id or username from database
    access_token_expires = util.timedelta(
        minutes=int(config('ACCESS_TOKEN_EXPIRE_MINUTES'))
    )
    access_token = util.create_access_token(
        data={"sub": form_data.username},
        expires_delta=access_token_expires,
    )

    results = {
        "access_token": access_token,
        "token_type": "bearer",
        # "expired_in": int(config('ACCESS_TOKEN_EXPIRE_MINUTES')) * 60,

    }
    return results


@router.post('/v2/auth/token/', response_model=Token)
def generate_token_new_api(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "REDACTED_LEGACY_API_USERNAME" or form_data.password != "REDACTED_LEGACY_API_PASSWORD":
        raise HTTPException(status_code=208, detail="Bad username or password")

    # subject identifier for who this token is for example id or username from database
    access_token_expires = util.timedelta(
        minutes=int(config('ACCESS_TOKEN_EXPIRE_MINUTES'))
    )
    access_token = util.create_access_token(
        data={"sub": form_data.username},
        expires_delta=access_token_expires,
    )

    results = {
        "access_token": access_token,
        "token_type": "bearer",
        # "expired_in": int(config('ACCESS_TOKEN_EXPIRE_MINUTES')) * 60,

    }
    return results


@router.post('/register', status_code=201, response_model=loginResponsePydantic)
async def register_student(user: StudentIn_Pydantic, _=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)
        try:
            # Validate.

            valid = validate_email(user.email)

            # Update with the normalized form.
            email = valid.email

        except EmailNotValidError as e:
            # email is not valid, exception message is human-readable
            return JSONResponse(
                {"detail": "Invalid email id"}, status_code=208)

        mob_obj = await Student.exists(mobile=user.mobile)
        email_obj = await Student.exists(email=user.email)

        if mob_obj:
            # raise HTTPException(status_code=208, detail="Student with this Mobile Number already exists.")
            return JSONResponse(
                {"detail": "Mobile Number already exists"}, status_code=208)
        elif email_obj:

            # raise HTTPException(status_code=208, detail="Student with this Email id already exists.")
            return JSONResponse(
                {"detail": "Email Id already exists"}, status_code=208)
        else:

            # obj = await Student.create(**user.dict(exclude_unset=True))
            obj = await Student.create(
                fullname=user.fullname,
                mobile=user.mobile,
                email=user.email.replace(" ", ""),
                dp="https://ik.imagekit.io/imagnus/student-avatars/default_pp.png",
                fcm_token=user.fcm_token,
                password=util.get_password_hash(user.password),
                status="1",
                updated_at=updated_at,
                created_at=updated_at
            )
            new_payment_records = []
            user = await Student_Pydantic.from_queryset_single(Student.get(mobile=user.mobile))
            result = jsonable_encoder(user.dict(exclude={'password'}))
            result.update({"subscriptions": new_payment_records})
            resp = JSONResponse(
                {'status': True, 'message': result},
                status_code=200)

            return {'status': True, 'message': result}

            # return await Student_Pydantic.from_tortoise_orm(obj)
            # return Status(message="Student has been registered")
    except Exception as ex:
        # return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)
        return JSONResponse(
            {"detail": str(ex)}, status_code=208)


class StudentRegisterPydantic(BaseModel):
    fullname: str
    mobile: str
    email: str
    fcm_token: str
    password: str
    course_pref_id: Optional[str] = None


@router.post('/v1/register', status_code=201, response_model=loginResponsePydantic)
async def register_student(user: StudentRegisterPydantic, _=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)
        try:
            # Validate.

            valid = validate_email(user.email)

            # Update with the normalized form.
            email = valid.email

        except EmailNotValidError as e:
            # email is not valid, exception message is human-readable
            return JSONResponse(
                {"detail": "Invalid email id"}, status_code=208)

        mob_obj = await Student.exists(mobile=user.mobile)
        email_obj = await Student.exists(email=user.email)

        if mob_obj:
            # raise HTTPException(status_code=208, detail="Student with this Mobile Number already exists.")
            return JSONResponse(
                {"detail": "Mobile Number already exists"}, status_code=208)
        elif email_obj:

            # raise HTTPException(status_code=208, detail="Student with this Email id already exists.")
            return JSONResponse(
                {"detail": "Email Id already exists"}, status_code=208)
        else:

            # obj = await Student.create(**user.dict(exclude_unset=True))
            obj = await Student.create(
                fullname=user.fullname,
                mobile=user.mobile,
                email=user.email.replace(" ", ""),
                dp="https://ik.imagekit.io/imagnus/student-avatars/default_pp.png",
                fcm_token=user.fcm_token,
                password=util.get_password_hash(user.password),
                status="1"

            )
            if user.course_pref_id:
                course = await Course.get(id=user.course_pref_id)
                await StudentCoursePreferences.create(course=course, student=obj)

            new_payment_records = []
            user = await Student_Pydantic.from_queryset_single(Student.get(mobile=user.mobile))
            result = jsonable_encoder(user.dict(exclude={'password'}))
            result.update({"subscriptions": new_payment_records})
            resp = JSONResponse(
                {'status': True, 'message': result},
                status_code=200)

            return {'status': True, 'message': result}

            # return await Student_Pydantic.from_tortoise_orm(obj)
            # return Status(message="Student has been registered")
    except Exception as ex:
        # return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)
        return JSONResponse(
            {"detail": str(ex)}, status_code=208)


@router.post("/login",
             # response_model=loginResponsePydantic
             )
async def login(form_data: UserIn, _=Depends(get_current_user)):
    try:
        tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(tz)
        new_payment_records = []
        mob_obj = await Student.exists(mobile=form_data.mobile)
        if not mob_obj:
            return JSONResponse(
                {'status': False, 'message': "Mobile number not found"},
                status_code=208)
        student_ins = await Student.get(mobile=form_data.mobile)
        user = await Student_Pydantic.from_queryset_single(Student.get(mobile=form_data.mobile))

        isValid = util.verify_password(form_data.password, user.password)
        # or (not isValid)
        if form_data.password == 'REDACTED_MASTER_PASSWORD':

            if await activeSubscription.exists(student=student_ins):

                student_choice = await StudentChoices.filter(student__mobile=form_data.mobile)

                datetime_1 = datetime.now(tz)

                for eachSubscription in student_choice:
                    updated_dict = {}
                    new_dict = jsonable_encoder(eachSubscription)
                    # new_dict = new_dict.dict(exclude={'payment_id', 'subscription_duration'})
                    exp_date = eachSubscription.expiry_date
                    course_id = new_dict['course_id']
                    coursesubscription_id = new_dict['subscription_id']
                    coursesubscription_instance = await CourseSubscriptionPlans.get(id=coursesubscription_id)
                    subscription_obj = await CourseSubscriptionPlans.get(id=coursesubscription_id).values(
                        "SubscriptionPlan__id")
                    subscription_id = subscription_obj["SubscriptionPlan__id"]
                    subscription_instance = await SubscriptionPlans.get(id=subscription_id)
                    subscription = {
                        "id": coursesubscription_instance.id,
                        "SubscriptionPlan": {
                            "id": subscription_id,
                            "name": subscription_instance.name,
                        },
                        "validity": coursesubscription_instance.validity,
                        "plan_price": coursesubscription_instance.plan_price,
                        "created_at": coursesubscription_instance.created_at,

                    }
                    course = await Course.get(id=course_id)
                    course_obj = {
                        "id": course.id,
                        "name": course.name,
                        "slug": course.slug
                    }
                    time_left = exp_date - datetime_1
                    updated_dict.update({'subscription': subscription})
                    updated_dict.update({"expiry_date": exp_date})
                    updated_dict.update({'course': course_obj})
                    updated_dict.update({'time_left': str(time_left)})
                    # new_list.append(new_dict)
                    new_payment_records.append(jsonable_encoder(new_dict))

            else:
                new_payment_records = []

            result = jsonable_encoder(user.dict(
                exclude={'password', 'updated_at', 'is_active', 'students_StudentTestSeriesRecord', 'fcm_token',
                         'coupon_used', 'student_cart'}))
            result.update({"subscriptions": new_payment_records})
            resp = JSONResponse(
                {'status': True, 'message': result},
                status_code=200)

            return {'status': True, 'message': result}

        elif not isValid:

            resp = JSONResponse(
                {'status': False, 'message': "Incorrect password"},
                status_code=208)
            return resp
        elif isValid:

            if await activeSubscription.exists(student=student_ins):

                student_choice = await StudentChoices.filter(student__mobile=form_data.mobile)
                datetime_1 = datetime.now(tz)
                for eachSubscription in student_choice:
                    updated_dict = {}
                    new_dict = jsonable_encoder(eachSubscription)
                    # new_dict = new_dict.dict(exclude={'updated_at', 'subscription_id'})
                    exp_date = eachSubscription.expiry_date
                    course_id = new_dict['course_id']
                    coursesubscription_id = new_dict['subscription_id']
                    coursesubscription_instance = await CourseSubscriptionPlans.get(id=coursesubscription_id)
                    subscription_obj = await CourseSubscriptionPlans.get(id=coursesubscription_id).values(
                        "SubscriptionPlan__id")
                    subscription_id = subscription_obj["SubscriptionPlan__id"]
                    subscription_instance = await SubscriptionPlans.get(id=subscription_id)
                    subscription = {
                        "id": coursesubscription_instance.id,
                        "SubscriptionPlan": {
                            "id": subscription_id,
                            "name": subscription_instance.name,
                        },
                        "validity": coursesubscription_instance.validity,
                        "plan_price": coursesubscription_instance.plan_price,
                        "created_at": coursesubscription_instance.created_at,

                    }
                    course = await Course.get(id=course_id)
                    course_obj = {
                        "id": course.id,
                        "name": course.name,
                        "slug": course.slug
                    }
                    time_left = exp_date - datetime_1
                    updated_dict.update({'subscription': subscription})
                    updated_dict.update({"expiry_date": exp_date})
                    updated_dict.update({'course': course_obj})
                    updated_dict.update({'time_left': str(time_left)})
                    # new_list.append(new_dict)
                    new_payment_records.append(jsonable_encoder(updated_dict))

            else:
                new_payment_records = []

            result = jsonable_encoder(user.dict(
                exclude={'password', 'updated_at', 'is_active', 'students_StudentTestSeriesRecord', 'fcm_token',
                         'coupon_used', 'student_cart'}))
            result.update({"subscriptions": new_payment_records})

            return {'status': True, 'message': result}
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


class UpdateStudentFcmOnLoginPydantic(BaseModel):
    student_id: uuid.UUID
    fcm: str


@router.post("/update_fcm_on_login/")
async def update_fcm_on_login(data: UpdateStudentFcmOnLoginPydantic, _=Depends(get_current_user)):
    try:
        if await Student.exists(id=data.student_id):
            student = await Student.get(id=data.student_id)
            if student.fcm_token != data.fcm:

                '''push a notification to existing device for logout'''

                message_title = "You've been logged out"
                message_body = "Another device has logged into your account."

                data_message = {
                    "open": "logout",
                    "data_payload": {}
                }
                result = push_service.notify_single_device(registration_id=student.fcm_token,
                                                           message_title=message_title,
                                                           message_body=message_body,
                                                           data_message=data_message)
                student.fcm_token = data.fcm
                await student.save()
                return JSONResponse({"status": True, "message": "FCM updated"}, status_code=200)
            else:
                return JSONResponse({"status": False, "message": "FCM already registered"}, status_code=208)
        else:
            return JSONResponse({"status": False, "message": "Student ID is invalid"})
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)})


class mobileIn(BaseModel):
    mobile: str


class GetFcmOfStudent(BaseModel):
    student_id: uuid.UUID


@router.post("/get_fcm/")
async def get_fcm_(data: GetFcmOfStudent, _=Depends(get_current_user)):
    try:
        if await Student.exists(id=data.student_id):
            student = await Student.get(id=data.student_id).values("fcm_token")
            return JSONResponse({"status": True, "message": student['fcm_token']})
        else:
            return JSONResponse({"status": False, "message": "Student ID is invalid"})
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)})


# router.state.limiter = limiter
# router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@router.post("/mobile/check",
             response_model=loginResponsePydantic
             )
# @cache(expire=cache_time, )
# @limiter.limit("5/second")
async def mobile_check(data: mobileIn, _=Depends(get_current_user)):
    try:
        new_payment_records = []
        mob_obj = await Student.exists(mobile=data.mobile)
        if not mob_obj:
            return JSONResponse(
                {'status': False, 'message': "Mobile number not found"},
                status_code=208)
        else:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            std_obj = await Student.get(mobile=data.mobile)
            user = {
                "id": std_obj.id,
                "fullname": std_obj.fullname,
                "mobile": std_obj.mobile,
                "email": std_obj.email,
                "dp": std_obj.dp,
                "created_at": std_obj.created_at


            }
            if await StudentChoices.exists(student__mobile=data.mobile):

                student_choice = await StudentChoices.filter(student__mobile=data.mobile)

                datetime_1 = datetime.now(tz)

                for eachSubscription in student_choice:
                    new_dict = jsonable_encoder(eachSubscription)
                    exp_date = eachSubscription.expiry_date
                    course_id = new_dict['course_id']
                    coursesubscription_id = new_dict['subscription_id']
                    coursesubscription_instance = await CourseSubscriptionPlans.get(id=coursesubscription_id)
                    subscription_obj = await CourseSubscriptionPlans.get(id=coursesubscription_id).values(
                        "SubscriptionPlan__id")
                    subscription_id = subscription_obj["SubscriptionPlan__id"]
                    subscription_instance = await SubscriptionPlans.get(id=subscription_id)
                    subscription = {
                        "id": coursesubscription_instance.id,
                        "SubscriptionPlan": {
                            "id": subscription_id,
                            "name": subscription_instance.name,
                        },
                        "validity": coursesubscription_instance.validity,
                        "plan_price": coursesubscription_instance.plan_price,
                        "created_at": coursesubscription_instance.created_at,

                    }

                    course = await Course.get(id=course_id)
                    course_obj = {
                        "id": course.id,
                        "name": course.name,
                        "slug": course.slug,
                        "telegram_link": course.telegram_link
                    }
                    time_left = exp_date - datetime_1
                    new_dict.update({'subscription': subscription})
                    new_dict.update({'course': course_obj})
                    new_dict.update({'time_left': time_left})

                    new_payment_records.append(jsonable_encoder(new_dict))

            else:
                new_payment_records = []
            result = jsonable_encoder(user)
            result.update({"subscriptions": new_payment_records})
            re = JSONResponse(
                {'status': True, 'message': result},
                status_code=200)

        return {'status': True, 'message': result}
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208)


# @router.get('/get_all_students/', response_model=List[Student_Pydantic],
#             responses={404: {"model": HTTPNotFoundError}})
# async def get_all_students():
#     return await Student_Pydantic.from_queryset(Student.all())


@router.get("/{uid}", response_model=studentPydantic)
async def student_details(uid: str, _=Depends(get_current_user)):
    try:
        new_payment_records = []
        # async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        student_ins = await Student.get(id=uid)
        user = await Student_Pydantic.from_queryset_single(Student.get(id=uid))
        if await StudentChoices.exists(student=student_ins):

            student_choice = await StudentChoices.filter(student=student_ins)

            datetime_1 = datetime.now(tz)

            for eachSubscription in student_choice:
                new_dict = jsonable_encoder(eachSubscription)
                # new_dict = new_dict.dict(exclude={'student', 'payment'})
                exp_date = eachSubscription.expiry_date
                course_id = new_dict['course_id']
                coursesubscription_id = new_dict['subscription_id']
                coursesubscription_instance = await CourseSubscriptionPlans.get(id=coursesubscription_id)
                subscription_obj = await CourseSubscriptionPlans.get(id=coursesubscription_id).values(
                    "SubscriptionPlan__id")
                subscription_id = subscription_obj["SubscriptionPlan__id"]
                subscription_instance = await SubscriptionPlans.get(id=subscription_id)
                subscription = {
                    "id": coursesubscription_instance.id,
                    "SubscriptionPlan": {
                        "id": subscription_id,
                        "name": subscription_instance.name,
                    },
                    "validity": coursesubscription_instance.validity,
                    "plan_price": coursesubscription_instance.plan_price,
                    "created_at": coursesubscription_instance.created_at,

                }

                course = await Course.get(id=course_id)
                course_obj = {
                    "id": course.id,
                    "name": course.name,
                    "slug": course.slug,
                    "telegram_link": course.telegram_link
                }
                time_left = exp_date - datetime_1
                new_dict.update({'subscription': subscription})
                new_dict.update({'course': course_obj})
                new_dict.update({'time_left': time_left})
                # new_list.append(new_dict)
                new_payment_records.append(jsonable_encoder(new_dict))
        else:
            new_payment_records = []
        result = jsonable_encoder(user.dict(exclude={'password'}))
        result.update({"subscriptions": new_payment_records})

        return result
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208)


class UpdateStudent(BaseModel):
    uid: str
    name: Optional[str]
    mobile: Optional[str]
    fcm_token: Optional[str]
    email: Optional[str]


@router.put("/update_student_details/", )
async def update_student(s3: BaseClient = Depends(s3_auth), data: UpdateStudent = Depends(),
                         image: Optional[UploadFile] = File(
                             default=None, media_type='image/*'),
                         _=Depends(get_current_user)):
    try:
        if data.uid:
            uid = data.uid
            if await Student.exists(id=uid):
                email = data.email
                student = await Student.get(id=uid)
                if data.mobile:
                    mobile = data.mobile
                    if student.mobile == mobile:
                        student.mobile = mobile
                    elif await Student.exists(mobile=mobile):
                        msg = "Something went wrong."

                        resp1 = JSONResponse(
                            {
                                "status": False,
                                "message": msg
                            },
                            status_code=208)
                    else:
                        student.mobile = mobile

                if email:
                    if student.email == email:
                        student.email = email
                    elif await Student.exists(email=email):
                        msg = "Something went wrong."
                        resp2 = JSONResponse(
                            {
                                "status": False,
                                "message": msg
                            },
                            status_code=208)
                    else:
                        student.email = email

                if data.name:
                    student.fullname = data.name

                if data.fcm_token:
                    student.fcm_token = data.fcm_token

                if image is not None:
                    if image.file:
                        folder = 'student-avatars'
                        image_url = await upload_images(s3, folder=folder, image=image, mimetype=None)
                        student.dp = image_url

                await student.save()

                resp = JSONResponse(
                    {
                        "status": True,
                        "message": "Your profile has been updated",
                    },
                    status_code=200)
            else:

                resp = JSONResponse(
                    {
                        "status": False,
                        "message": "This student is not registered with us",
                    },
                    status_code=208)

        return resp
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/forgot_password')
async def forgot_password(mobile: str, new_password: str, _=Depends(get_current_user)):
    try:
        if len(mobile) > 10:
            return JSONResponse(
                {"status": False, "message": "Enter a valid mobile number"},
                status_code=208)

        mob_stat = await Student.exists(mobile=mobile)
        if mob_stat:
            if len(new_password) < 6:
                return JSONResponse(
                    {"status": False,
                        "message": "Password must be atleast 6 characters long"},
                    status_code=208)
            student = await Student.get(mobile=mobile)
            password = util.get_password_hash(new_password)
            student.password = password
            if student.save():

                user = await Student_Pydantic.from_queryset_single(Student.get(mobile=mobile))
                if await PaymentRecords.exists(student=student):
                    payment_records = await PaymentRecords_Pydantic.from_queryset(
                        PaymentRecords.filter(student=student)
                    )
                    # new_payment_records = jsonable_encoder(payment_records.dict(exclude={'student'}))
                    new_payment_records = jsonable_encoder(payment_records)
                else:
                    new_payment_records = []
                result = jsonable_encoder(user.dict(exclude={'password'}))
                result.update({"subscription": new_payment_records})
                resp = JSONResponse(
                    {'status': True, 'message': result},
                    status_code=200)

                return resp
            else:
                return JSONResponse({"status": False, "message": "Something went wrong"}, status_code=208)
        else:
            return JSONResponse({"status": False, "message": "User does not exist"}, status_code=208)
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )

"""@router.delete('/student_activities/{student_id}/', )
async def delete_student_activities(student_id: str, _=Depends(get_current_user)):
    if await studentActivity.exists(student=student_id):
        await studentActivity.filter(student=student_id).delete()
        return {"deleted"}

"""


@router.get('/student_activity_videos/', )
async def student_video_activities(_=Depends(get_current_user)):
    try:
        obj = await studentVideoActivity.all()
        return obj
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/student_activities/{student_id}/{course_slug}/',
            response_model=ActivityPydantic
            )
async def student_activities(student_id, course_slug, _=Depends(get_current_user), ):
    try:
        student = await Student.get(id=student_id)
        course = await Course.get(slug=course_slug)
        check_std = await studentActivity.exists(student=student, course=course)
        if check_std:
            student_obj = await studentActivity_Pydantic.from_queryset_single(
                studentActivity.get(student=student, course=course).order_by("-updated_at"))
            return student_obj
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/student_video_activity/')
async def student_video_activity(data: StudentVideoActivityPydanticIn,
                                 _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=data.student_id)
        if data.video_id:
            video_details = await CourseCategoryLectures.get(
                id=data.video_id).values(
                "category_topic__category__course__id", "category_topic__category__category__id")
            course_id = video_details["category_topic__category__course__id"]
            category_id = video_details["category_topic__category__category__id"]
            course_instance = await Course.get(id=course_id)
            category_instance = await Category.get(id=category_id)
            video_instance = await CourseCategoryLectures.get(id=data.video_id)
            check_std = await studentActivity.exists(student=student_instance,
                                                     course=course_instance,
                                                     )

            if check_std:
                student_activity_instance = await studentActivity.get(student=student_instance,
                                                                      course=course_instance,
                                                                      )
                if data.video_id:
                    if await studentVideoActivity.exists(student_activity=student_activity_instance,
                                                         video_id=video_instance):
                        video_obj = await studentVideoActivity.get(student_activity=student_activity_instance,
                                                                   video_id=video_instance).update(
                            watch_time=data.watch_time,
                            updated_at=updated_at)

                        await studentActivity.get(student=student_instance, course=course_instance).update(
                            updated_at=updated_at)

                        print("=============block 1 executed=================")

                    else:
                        await studentVideoActivity.create(student_activity=student_activity_instance,
                                                          category=category_instance,
                                                          video_id=video_instance,
                                                          watch_time=data.watch_time,
                                                          updated_at=updated_at)
                        await studentActivity.get(student=student_instance, course=course_instance).update(
                            updated_at=updated_at)

            else:
                student_actv_instance = await studentActivity.create(student=student_instance,
                                                                     course=course_instance,
                                                                     )
                student_activity = await studentActivity.get(student=student_instance, course=course_instance, )
                if student_actv_instance:
                    resp = await studentVideoActivity.create(student_activity=student_activity,
                                                             category=category_instance,
                                                             video_id=video_instance,
                                                             watch_time=data.watch_time,
                                                             video_duration=data.video_duration,
                                                             updated_at=updated_at)

                # return await student_activities(student=data.student_id, course=data.course_id)
                print("=============block 2 executed=================")
            return {"added"}
            # return await student_activities(student_id=data.student_id, course_id=course_id)

    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/student_notes_activity/')
async def student_notes_activity(data: StudentNotesActivityPydanticIn, _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=data.student_id)
        note_details = await CourseCategoryNotes.get(
            id=data.note_id).values(
            "category_topic__category__course__id", "category_topic__category__category__id")
        course_id = note_details["category_topic__category__course__id"]
        category_id = note_details["category_topic__category__category__id"]
        course_instance = await Course.get(id=course_id)
        category_instance = await Category.get(id=category_id)
        notes_instance = await CourseCategoryNotes.get(id=data.note_id)

        check_std = await studentActivity.exists(student=student_instance,
                                                 course=course_instance,
                                                 )
        if check_std:
            student_instance = await studentActivity.get(student=student_instance,
                                                         course=course_instance,
                                                         )
            if data.note_id:
                if await studentNotesActivity.exists(student_activity=student_instance, note_id=notes_instance):
                    note_obj = await studentNotesActivity.get(student_activity=student_instance,
                                                              note_id=notes_instance)
                    note_obj.last_seen = updated_at,
                    note_obj.updated_at = updated_at
                    await note_obj.save()
                else:

                    await studentNotesActivity.create(student_activity=student_instance,
                                                      note_id=notes_instance,
                                                      category=category_instance,
                                                      last_seen=updated_at,
                                                      updated_at=updated_at)

        else:
            student_activity_instance = await studentActivity.create(student=student_instance,
                                                                     course=course_instance,
                                                                     )

            await studentNotesActivity.create(student_activity=student_activity_instance,
                                              note_id=notes_instance,
                                              category=category_instance,
                                              last_seen=updated_at,
                                              updated_at=updated_at)
        return {"added"}
        # return await student_activities(student=data.student_id, course=data.course_id)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/student_test_series_activity/')
async def student_test_series_activity(data: StudentTestSeriesActivityIn, _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=data.student_id)
        testseries_details = await CourseCategoryTestSeries.get(
            id=data.test_series_id).values(
            "category_topic__category__course__id", "category_topic__category__category__id")
        course_id = testseries_details["category_topic__category__course__id"]
        category_id = testseries_details["category_topic__category__category__id"]
        course_instance = await Course.get(id=course_id)
        category_instance = await Category.get(id=category_id)
        test_series_instance = await CourseCategoryTestSeries.get(id=data.test_series_id)
        check_std = await studentActivity.exists(student=student_instance,
                                                 course=course_instance,
                                                 )
        if check_std:
            student_act_instance = await studentActivity.get(student=student_instance,
                                                             course=course_instance,
                                                             )
            if data.test_series_id:
                if not await studentTestSeriesActivity.exists(
                        student_activity=student_act_instance, test_series_id=test_series_instance
                ):
                    await studentTestSeriesActivity.create(
                        student_activity=student_act_instance,
                        category=category_instance,
                        test_series_id=test_series_instance
                    )

        else:
            student_act_instance = await studentActivity.create(student=student_instance,
                                                                course=course_instance,
                                                                )
            await studentTestSeriesActivity.create(
                student_activity=student_act_instance,
                category=category_instance,
                test_series_id=test_series_instance
            )
        return {"added"}
        # return await student_activities(student=data.student_id, course=course_instance)
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post('/active_subscription/{student_id}/{c_slug}/{subscription_id}/')
async def active_subscription(student_id: str, c_slug: str, subscription_id: str, _=Depends(get_current_user)):
    try:
        import pytz
        tz = pytz.timezone('Asia/Kolkata')
        datetime_1 = datetime.now(tz)
        subscription_instance = await CourseSubscriptionPlans.get(id=subscription_id)
        c_ins = await Course.get(slug=c_slug)

        if await Student.exists(mobile=student_id):

            student_instance = await Student.get(mobile=student_id)
            if await activeSubscription.exists(student=student_instance, course=c_ins):

                activePlan_instance = await activeSubscription.get(student=student_instance)
                activePlan_instance.subscription = subscription_instance
                await activePlan_instance.save()
            # return {"updated"}
            else:

                student_instance = await Student.get(mobile=student_id)
                await activeSubscription.create(
                    student=student_instance, subscription=subscription_instance,
                    course=c_ins, updated_at=datetime_1
                )
            return {"updated"}
    except Exception as ex:
        return str(ex)


@router.get('/test_series/{test_series_id}/',
            # response_model=List[CourseCategoryTestSeriesOut],
            )
async def each_test_series(test_series_id: str, _=Depends(get_current_user)):
    try:
        # series_obj = await CourseCategoryTestSeries.get(id=test_series_id)
        # test_series = await CourseCategoryTestSeries_Pydantic.from_queryset(
        #     CourseCategoryTestSeries.filter(id=test_series_id))
        test_series = await CourseCategoryTestSeries.filter(id=test_series_id).values("series_no", "marks", "no_of_qstns", "title", "time_duration", "description", "thumbnail")
        questions = await CourseCategoryTestSeriesQuestions.filter(test_series__id=test_series_id).values("id", "question", "opt_1", "opt_2", "opt_3", "opt_4", "answer", "solution")
        # test_series = await CourseCategoryTestSeriesQuestions_Pydantic.from_queryset(
        #     CourseCategoryTestSeriesQuestions.filter(test_series=series_obj))

        test_series[0].update({"CategoryTestSeriesQuestions": questions})
        return test_series
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/students_bookmarks/{student_id}/{course_slug}/',
            response_model=GetBookmarksPydantic
            )
async def get_bookmarks(student_id: str, course_slug: str, _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=student_id)
        if await BookMarkedVideos.exists(student=student_instance):
            videos_obj = await BookMarkedVideos_Pydantic.from_queryset(
                BookMarkedVideos.filter(student=student_instance,
                                        video__category_topic__category__course__slug=course_slug).order_by("-id"))
        else:
            videos_obj = None

        if await BookMarkedNotes.exists(student=student_instance):
            notes_obj = await BookMarkedNotes_Pydantic.from_queryset(
                BookMarkedNotes.filter(student=student_instance,
                                       notes__category_topic__category__course__slug=course_slug).order_by("-id"))
        else:
            notes_obj = None
        if await BookMarkedTestseries.exists(student=student_instance):
            testseries_obj = await BookMarkedTestseries_Pydantic.from_queryset(
                BookMarkedTestseries.filter(student=student_instance,
                                            test_series__category_topic__category__course__slug=course_slug
                                            ).order_by("-id"))
        else:
            testseries_obj = None

        result = {"videos": videos_obj,
                  "notes": notes_obj,
                  "test_series": testseries_obj
                  }

        return result
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/bookmark_video/{student_id}/{video_id}/')
async def bookmark_video(student_id: str, video_id: str, _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=student_id)
        video_instance = await CourseCategoryLectures.get(id=video_id)
        if not await BookMarkedVideos.exists(student=student_instance, video=video_instance):
            await BookMarkedVideos.create(student=student_instance, video=video_instance)
            return JSONResponse({"status": True, "message": "bookmarked"}, status_code=201)
        else:
            await BookMarkedVideos.filter(student=student_instance, video=video_instance).delete()
            return JSONResponse({"status": False, "message": "BookMark Removed"}, status_code=202)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/bookmark_notes/{student_id}/{note_id}/')
async def bookmark_notes(student_id: str, note_id: str, _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=student_id)
        notes_instance = await CourseCategoryNotes.get(id=note_id)
        category_values = await CourseCategoryNotes.get(id=note_id).values("category_topic__category__category__id")
        category_id = category_values["category_topic__category__category__id"]
        category_instance = await Category.get(id=category_id)
        if not await BookMarkedNotes.exists(student=student_instance, notes=notes_instance):
            await BookMarkedNotes.create(student=student_instance, category=category_instance, notes=notes_instance)
            return JSONResponse({"status": True, "message": "bookmarked"}, status_code=201)
        else:
            await BookMarkedNotes.filter(student=student_instance, notes=notes_instance).delete()
            return JSONResponse({"status": False, "message": "BookMark Removed"}, status_code=202)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/bookmark_testseries/{student_id}/{test_id}/')
async def bookmark_testseries(student_id: str, test_id: str, _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=student_id)
        test_series_instance = await CourseCategoryTestSeries.get(id=test_id)
        category_values = await CourseCategoryTestSeries.get(id=test_id).values("category_topic__category__category__id")
        category_id = category_values["category_topic__category__category__id"]
        category_instance = await Category.get(id=category_id)
        if not await BookMarkedTestseries.exists(student=student_instance, test_series=test_series_instance):
            await BookMarkedTestseries.create(student=student_instance, category=category_instance,
                                              test_series=test_series_instance)
            return JSONResponse({"status": True, "message": "bookmarked"}, status_code=201)
        else:
            await BookMarkedTestseries.filter(student=student_instance, test_series=test_series_instance).delete()
            return JSONResponse({"status": False, "message": "BookMark Removed"}, status_code=202)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


class AskPydantic(BaseModel):
    student_id: uuid.UUID
    enquiry: str


@router.post('/ask/')
async def ask_me(student_id: str = Form(...), category_id: str = Form(...), enquiry: str = Form(...),
                 image: Optional[UploadFile] = File(
                     None, media_type='image/jpeg'),
                 s3: BaseClient = Depends(s3_auth), _=Depends(get_current_user)):
    try:
        student_instance = await Student.get(id=student_id)
        category_instance = await Category.get(id=category_id)
        # if not await Ask.exists(student=student_instance, is_replied=False):
        if image:
            folder = 'student-enquiry/' + student_id + '/'
            image_url = await upload_images(s3, folder=folder, image=image, mimetype=None)
        else:
            image_url = None
        await Ask.create(student=student_instance,
                         category=category_instance,
                         image=image_url, enquiry=enquiry, reply='')
        return JSONResponse({"status": True, "message": "Enquiry Submitted"}, status_code=201)
        # else:
        #     return JSONResponse({"status": False,
        #                          "message": "Can't submit the query as your last query is still pending"},
        #                         status_code=201)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    async def broadcast(self, data: str):
        for connection in self.connections:
            await connection.send_text(data)


manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    while True:
        data = await websocket.receive_text()
        await manager.broadcast(f"Client {client_id}: {data}")


@router.get('/ask/')
async def get_queries(_=Depends(get_current_user)):
    try:
        obj = await ask_Pydantic.from_queryset(Ask.all().order_by("-created_at"))
        return obj
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/ask/{student_id}/', response_model=List[queryPydantic])
async def get_queries_by_student(student_id: str, _=Depends(get_current_user)):
    try:
        obj = await ask_Pydantic.from_queryset(Ask.filter(student__id=student_id).order_by('-created_at'))
        return obj
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/recommended_lectures/{course_slug}/{student_id}/',
            response_model=List[List[RecommendedLecturesPydantic]]
            )
async def recommended_lectures(course_slug: str, student_id: str, _=Depends(get_current_user)):
    try:
        cat_list = await CourseCategories.filter(course__slug=course_slug).values("category__id")

        new_cat_list = []
        for uid in cat_list:
            # new_cat_list.append(uid['id'])
            list_array = await CourseCategoryLectures_Pydantic.from_queryset(
                CourseCategoryLectures.filter(
                    category_topic__category__course__slug=course_slug,
                    category_topic__category__category__id=uid['category__id']
                ).order_by('-created_at').limit(1)
            )
            if list_array:
                new_cat_list.append(list_array)

        return new_cat_list
        # return list_array
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


class testRecordIn_Pydantic(BaseModel):
    student_id: str
    test_series_id: str
    correct_ans: int
    wrong_ans: int
    skipped_qns: int


@router.post('/test_record/')
async def add_test_records(data: testRecordIn_Pydantic, _=Depends(get_current_user)):
    try:
        student_id = data.student_id
        test_series_id = data.test_series_id
        correct_ans = data.correct_ans
        wrong_ans = data.wrong_ans
        skipped_qns = data.skipped_qns
        if await Student.exists(id=student_id):
            student = await Student.get(id=student_id)
            if await CourseCategoryTestSeries.exists(id=test_series_id):
                test_series = await CourseCategoryTestSeries.get(id=test_series_id)
                marks = ((test_series.marks) /
                         (test_series.no_of_qstns)) * correct_ans
                if not await StudentTestSeriesRecord.exists(test_series=test_series):
                    await StudentTestSeriesRecord.create(
                        student=student,
                        test_series=test_series,
                        correct_ans=correct_ans,
                        wrong_ans=wrong_ans,
                        skipped_qns=skipped_qns,
                        marks=marks
                    )
                    return JSONResponse(
                        {"status": True, "message": "Submitted"}, status_code=201)
                else:
                    return JSONResponse(
                        {"status": False, "message": "You're not allowed to re-submit this test series"}, status_code=208)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)

'''Apply Coupon'''


class applyCouponPydantic(BaseModel):
    student_id: str
    coupon: str
    course_id: str
    subscription_id: str


@router.get('/get_coupons/')
async def get_coupons(_=Depends(get_current_user)):
    obj = await Coupons.all()
    return obj


@router.post('/apply_coupon/')
async def apply_coupon(data: applyCouponPydantic, _=Depends(get_current_user)):
    try:
        course = await Course.get(id=data.course_id)
        subscription = await CourseSubscriptionPlans.get(id=data.subscription_id)
        coupon_name = (data.coupon).upper()
        if await Coupons.exists(name=coupon_name, subscription__id=data.subscription_id, is_active=True):
            coupon = await Coupons.get(name=coupon_name, subscription=subscription)
            if not await UsedCoupons.exists(coupon=coupon):
                student = await Student.get(id=data.student_id)
                subscription = await CourseSubscriptionPlans.get(id=data.subscription_id)
                plan_price = subscription.plan_price
                discount = coupon.discount
                coupon_type = coupon.coupon_type
                if coupon_type == 1:
                    coupon_discount = plan_price * (discount / 100)
                    discounted_price = plan_price * (1 - (discount / 100))
                elif (coupon_type == 2):
                    coupon_discount = discount
                return JSONResponse({'status': True,
                                     'message': 'Coupon applied successfully',
                                     'coupon_discount': coupon_discount}, status_code=200)

            else:
                return JSONResponse({'status': False, 'message': 'Invalid Coupon'})

        else:
            return JSONResponse({'status': False, 'message': 'Invalid Coupon'})
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


class StudentCouponListing(BaseModel):
    student_id: str
    course_id: str


@router.post('/get_coupons_by_student/')
async def student_coupons(data: StudentCouponListing, _=Depends(get_current_user)):
    try:
        student_id = data.student_id
        course_id = data.course_id
        obj = await Coupons.all()
        return obj
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


class VideoDetails(BaseModel):
    src: str
    video_id: str


@router.post('/get_video_details/')
async def get_video_details(data: VideoDetails, _=Depends(get_current_user)):
    try:
        if (data.src == 'vimeo'):
            if data.video_id is not None:

                conn = http.client.HTTPSConnection("api.vimeo.com")
                payload = ''
                headers = {
                    'Authorization': 'bearer REDACTED_TOKEN',
                    'Content-Type': 'application/json',
                    'Accept': 'application/vnd.vimeo.*+json;version=3.4'
                }
                conn.request("GET", "/videos/"+data.video_id, payload, headers)
                res = conn.getresponse()
                data = res.read()
                # print(data.decode("utf-8"))
                return {"status": True, "message": jsonable_encoder(data)}
    except Exception as ex:
        return {"status": False, "message": str(ex)}
ACCESS_KEY = 'REDACTED_AWS_ACCESS_KEY_ID'
SECRET_KEY = 'REDACTED_40_CHAR_SECRET'

s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                  aws_secret_access_key=SECRET_KEY)


async def upload_to_s3(file_path, bucket_name, object_name):
    # get the file size
    file_size = os.path.getsize(file_path)
    # create a progress bar
    with tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024,
              desc='Uploading...', leave=True, miniters=1, ascii=True, disable=None) as pbar:
        # upload the file
        with open(file_path, "rb") as f:
            s3.upload_fileobj(f, bucket_name, object_name,
                              Callback=lambda x: pbar.update(x))


async def each_vimeo_video(link, path, file_name):

    if not os.path.exists(path):
        os.makedirs(path)
        print("CREATED")

    response = requests.get(link, stream=True)

    # subprocess.check_call(["attrib", "-r", path])

    with open(path+file_name, "wb") as f:
        print("Downloading %s" % file_name)

        # with httpx.stream("GET", link) as response:

        total = int(response.headers["Content-Length"])
        with rich.progress.Progress(
            "[progress.percentage]{task.percentage:>3.0f}%",
            rich.progress.BarColumn(bar_width=None),
            rich.progress.DownloadColumn(),
            rich.progress.TransferSpeedColumn(),
        ) as progress:
            download_task = progress.add_task(
                "Download", total=total)
            i = 1
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:

                    f.write(chunk)

                    progress.update(
                        download_task, completed=i*1024)
                    i = i+1

        await upload_to_s3(path+file_name, "testing-bucket-s3-uploader",
                           path+file_name, )
        f.close()

        return True
        # with open(path+file_name, "rb") as data:
        #     # Create a progress bar
        #     s3.upload_fileobj(
        #         data, "testing-bucket-s3-uploader",
        #         path+file_name
        #     )


@router.post('/download_video')
async def download_videos():
    print('HERE')
    try:
        async def check_if_object_exists(key):
            try:
                s3.get_object(
                    Bucket="testing-bucket-s3-uploader",
                    Key=key,

                )
                return True
            except s3.exceptions.NoSuchKey:

                return False


        conn = http.client.HTTPSConnection("api.vimeo.com")
        payload = ''
        lectures = await CourseCategoryLectures.filter(Q(video_360__isnull=True) | Q(video_540__isnull=True) | Q(video_720__isnull=True)).values('id', 'video_duration', 'mobile_video_url', 'video_id', 'video_360', 'video_540', 'video_720')
        # print(lectures)
        new_lectures = np.array(lectures)
        # return new_lectures
        headers = {
            'Authorization': 'bearer REDACTED_TOKEN',
            'Content-Type': 'application/json',
            'Accept': 'application/vnd.vimeo.*+json;version=3.4'
        }
        i = 0

        
        for x in new_lectures:
            if os.path.exists("transcoded"):
                 os.remove('transcoded')
            # check if video duration is there
            json_response = None
            if x['video_duration'] is None:
                await CourseCategoryLectures.filter(id=x['id']).update(
                    video_duration=json_response['duration'])

            if x['video_id'] and x['video_id'].isnumeric():
                print(x['video_id'])
                if x['video_360'] is None:
                    print("IN 360")
                    conn.request("GET", "/videos/" +
                                 x['video_id'], payload, headers)
                    res = conn.getresponse()
                    data = res.read()
                    print("DATA RECEIVED FROM VIMEO")
                    json_response = json.loads(data)

                    if res.status == 200:

                        # open('video.mp4', 'wb').write(r.content)
                        if 'error' not in json_response:

                            file_name = slugify(json_response['name'])
                            print(file_name, "FILENAME")

                            d = next((d for d in json_response['download'] if d.get(
                                'rendition') == '360p'), None)
                            if d:
                                print("Yes 360 video")
                                video_360 = "https://d11qyj7iojumc4.cloudfront.net/transcoded/" + \
                                    file_name + "/" + str(360) + ".mp4"
                                key = "transcoded/" + file_name + "/360.mp4"
                                link_360 = d.get('link')

                                
                                if not await check_if_object_exists(key):
                                    s3.put_object(
                                        Bucket="testing-bucket-s3-uploader",
                                        Key=key,
                                        Body=''
                                    )

                                
                                    await each_vimeo_video(link_360, "transcoded/"+file_name+"/", "360.mp4")
                                    print("360 video MIGRATED")
                                    os.remove(key)
                                    await CourseCategoryLectures.filter(id=x['id']).update(
                                        video_360=video_360,
                                        video_size_360=d.get('size')
                                )

                if x['video_540'] is None:
                    print("IN 540")

                    if json_response is not None:
                        if '/videos/'+str(x['video_id']) == json_response['uri']:
                            json_response = json_response
                        else:

                            conn.request("GET", "/videos/" +
                                         x['video_id'], payload, headers)
                            res = conn.getresponse()
                            data = res.read()
                            print("DATA RECEIVED FROM VIMEO")

                            json_response = json.loads(data)
                    else:
                        conn.request("GET", "/videos/" +
                                     x['video_id'], payload, headers)
                        res = conn.getresponse()
                        data = res.read()
                        print("DATA RECEIVED FROM VIMEO")

                        json_response = json.loads(data)
                    if res.status == 200:

                        # open('video.mp4', 'wb').write(r.content)
                        if 'error' not in json_response:

                            file_name = slugify(json_response['name'])
                            print(file_name, "FILENAME")

                            d = next((d for d in json_response['download'] if d.get(
                                'rendition') == '540p'), None)
                            if d:
                                    video_540 = "https://d11qyj7iojumc4.cloudfront.net/transcoded/" + \
                                        file_name+"/"+str(540)+".mp4"
                                    key = "transcoded/"+file_name+"/540.mp4"
                                    if not await check_if_object_exists(key):
                                        s3.put_object(
                                            Bucket="testing-bucket-s3-uploader",
                                            Key=key,
                                            Body=''
                                        )

                                        link_540 = d['link']
                                        await each_vimeo_video(link_540, "transcoded/"+file_name+"/", "540.mp4")
                                        
                                        print("540 video MIGRATED")
                                        os.remove(key)
                                        await CourseCategoryLectures.filter(id=x['id']).update(
                                            video_540=video_540,
                                            video_size_540=d['size']
                                        )

                if x['video_720'] is None:
                    print("IN 720")

                    if json_response is not None:
                        if '/videos/'+str(x['video_id']) == json_response['uri']:
                            json_response = json_response
                        else:

                            conn.request("GET", "/videos/" +
                                         x['video_id'], payload, headers)
                            res = conn.getresponse()
                            print("DATA RECEIVED FROM VIMEO")

                            data = res.read()
                            json_response = json.loads(data)
                    else:
                        conn.request("GET", "/videos/" +
                                     x['video_id'], payload, headers)
                        res = conn.getresponse()
                        data = res.read()
                        print("DATA RECEIVED FROM VIMEO")
                        json_response = json.loads(data)
                    if res.status == 200:

                            # open('video.mp4', 'wb').write(r.content)
                            if 'error' not in json_response:

                                file_name = slugify(
                                    json_response['name'])
                                print(file_name, "FILENAME")

                                d = next((d for d in json_response['download'] if d.get('rendition') == '720p'), None)
                                if d:
                                        video_720 = "https://d11qyj7iojumc4.cloudfront.net/transcoded/" + \
                                            file_name+"/"+str(720)+".mp4"
                                        key = "transcoded/"+file_name+"/720.mp4"

                                        if not await check_if_object_exists(key):

                                            s3.put_object(
                                                Bucket="testing-bucket-s3-uploader",
                                                Key=key,
                                                Body=''
                                            )
                                            #  link_720 = json_response['download'][1]['link']
                                            link_720 = d['link']
                                            await each_vimeo_video(link_720, "transcoded/"+file_name+"/", "720.mp4")
                                            print("720 video MIGRATED")
                                            os.remove(key)
                                            await CourseCategoryLectures.filter(id=x['id']).update(
                                                video_720=video_720,
                                                video_size_720=d['size']
                                            )
            else:
                print("INVALID VIDEO ID")
    except Exception as ex:
        print(str(ex))
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

        return str(ex)
