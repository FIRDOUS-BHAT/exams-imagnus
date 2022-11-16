import typing
from starlette_context import context
from dateutil import parser
import time
import json
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional
from typing import NewType
import httpx
import jwt
import pandas as pd
import pytz
import requests
from botocore.client import BaseClient
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, FastAPI, Request, Form, File, UploadFile, status, HTTPException, \
    WebSocket, Query
from fastapi.encoders import jsonable_encoder
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_login.exceptions import InvalidCredentialsException
from imagekitio import ImageKit
from pydantic import BaseModel
from slugify import slugify
from starlette.responses import RedirectResponse
from tortoise.contrib.fastapi import HTTPNotFoundError
from FCM.route import push_service
from admin_dashboard.models import *
from aws_services.deps import s3_auth
from aws_services.s3.upload import upload_file_to_bucket
from aws_services.settings import settings
from checkout.models import PaymentRecords, PaymentRecords_Pydantic
from configs import appinfo
from configs.connection import db_config
from scholarship_tests.models import ScholarshipTestSeries, ScholarshipTestSeriesQuestions, \
    ScholarshipTestSeries_Pydantic
from send_mails.models import StudentEnquiry_Pydantic, StudentEnquiry
from student.apis.pydantic_models import PNeachNewtestSeriesPydantic, PNeachNotePydantic, \
    PushNotificationsLecturesPydantic, eachNewtestSeriesPydantic
from student.controller import create_access_token
from student.models import Student, Student_Pydantic
from student_choices.models import Ask, StudentChoices, ask_Pydantic
from study_material.models import StudyMaterialOrderInstance, StudyMaterialOrderInstance_Pydantic, TestSeriesOrders, \
    TestSeriesOrders_Pydantic
from utils import util
from fastapi.responses import JSONResponse
tz = pytz.timezone('Asia/Kolkata')
updated_at = datetime.now(tz)

imagekit = ImageKit(
    private_key=settings.IMAGEKIT_PRIVATE_KEY,
    public_key=settings.IMAGEKIT_PUBLIC_KEY,
    url_endpoint='https://ik.imagekit.io/imagnus/'
)

router = APIRouter()
app = FastAPI(debug=True)
templates = Jinja2Templates(directory="admin_dashboard/templates/admin")


class CsrfSettings(BaseModel):
    secret_key: str = 'thisisimagnuswebapp'


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()
bunny_library_id = settings.bunny_library_id
bunny_host = settings.bunny_cdn_host
bunny_access_key = settings.bunny_access_key
app_url = settings.app_url


class Status(BaseModel):
    message: str


secret_key = settings.secret_key


def get_cookie(request: Request):
    try:
        token = request.cookies.get(settings.admin_login)
        return token
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


def flash(request: Request, message: typing.Any, category: str = "primary") -> None:
    if "_messages" not in request.session:
        request.session["_messages"] = []
    request.session["_messages"].append(
        {"message": message, "category": category})


def get_flashed_messages(request: Request):

    return request.session.pop("_messages") if "_messages" in request.session else []


templates.env.globals['get_flashed_messages'] = get_flashed_messages


async def check_login_auth():

    ips = context.data["X-Forwarded-For"]
    ips = "27.7.244.155,127.0.0.1"
    forwarded_for = ips.split(',')
    request_ip = forwarded_for[0]
    if await AdminLoginTracker.exists(ip=request_ip):
        print("True")
        return True
    else:
        print("False")
        return False


async def get_current_user(session: str = Depends(get_cookie)):
    try:

        if session is None:
            return None

        payload = jwt.decode(session, secret_key,
                             algorithms=[settings.algorithm])

        exp = payload.get("exp")

    except (jwt.DecodeError, jwt.ExpiredSignatureError):
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)

    user: uuid.UUID = payload.get("sub")

    student_ins = await Student.exists(id=user)

    if not student_ins:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    return user


@router.get('/admin/logout/')
async def logout(user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    ips = context.data["X-Forwarded-For"]
    # ips = "27.7.244.155,127.0.0.1"
    forwarded_for = ips.split(',')
    request_ip = forwarded_for[0]
    if await AdminLoginTracker.exists(ip=request_ip):
        ip_obj = await AdminLoginTracker.get(ip=request_ip)
        ip_obj.current_users = ip_obj.current_users - 1
        await ip_obj.save()
    resp = RedirectResponse(url='/administrator/login/',
                            status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(key=settings.admin_login)
    return resp


'''@router.post('/admin/register/')
async def admin_register(mobile: str, password: str):
    mob_obj = await Admin.exists(mobile=mobile)
    if mob_obj:
        return JSONResponse({"status": False, "message": "Mobile number already exists"}, status_code=208)

    await Admin.create(
        mobile=mobile,
        password=util.get_password_hash(password),
    )

    return JSONResponse({"status": True, "message": "Registered Successfully"}, status_code=200)

'''


@router.post('/secure/admin/login/')
async def login(request: Request, data: OAuth2PasswordRequestForm = Depends()):
    try:
        request_ip = request.client.host
        header = request.headers
        ips = context.data["X-Forwarded-For"]
        ips = "27.7.244.155,127.0.0.1"
        forwarded_for = ips.split(',')
        request_ip = forwarded_for[0]

        if await AccessToAdminArea.all().count() < 1:
            await AccessToAdminArea.create(is_enabled=True, allowed_users=1, current_users=0)
            if await AccessToAdminArea.exists(is_enabled=True):
                if not await AdminLoginTracker.exists(ip=request_ip):
                    await AdminLoginTracker.create(ip=request_ip, allowed_users=1, current_users=0)
                else:
                    trck_obj = await AdminLoginTracker.get(ip=request_ip)
                    trck_obj.allowed_users = trck_obj.allowed_users + 1
                    await trck_obj.save()
        elif await AccessToAdminArea.exists(is_enabled=True):
            if not await AdminLoginTracker.exists(ip=request_ip):

                await AdminLoginTracker.create(ip=request_ip, allowed_users=1, current_users=0)
            else:
                trck_obj = await AdminLoginTracker.get(ip=request_ip)
                trck_obj.allowed_users = trck_obj.allowed_users + 1
                await trck_obj.save()
        if await AdminLoginTracker.exists(ip=request_ip):
            ip_obj = await AdminLoginTracker.get(ip=request_ip)
            if ip_obj.current_users < ip_obj.allowed_users:
                print(request_ip)
                ip_obj.current_users = ip_obj.current_users + 1
                await ip_obj.save()
                mobile = data.username
                password = data.password
                mob_obj = await Admin.exists(mobile=mobile)

                if not mob_obj:
                    # request.session.update({"data": "Mobile number not found"})
                    flash(request, "Mobile number not found", "danger")

                    return RedirectResponse(url="/administrator/login/",
                                            status_code=status.HTTP_302_FOUND)
                admin = await Admin.get(mobile=mobile)

                if not admin:
                    flash(request, "Mobile number not found", "danger")
                isValid = util.verify_password(password, admin.password)

                if not isValid:
                    # request.session.update({"data": "Incorrect password"})
                    flash(request, "Incorrect password", "danger")

                    return RedirectResponse(url="/administrator/login/",
                                            status_code=status.HTTP_302_FOUND)

                access_token = create_access_token(
                    data=dict(sub=jsonable_encoder(admin.id)), expires=timedelta(
                        hours=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                )

                resp = RedirectResponse(url='/admin/',
                                        status_code=status.HTTP_302_FOUND)

                resp.set_cookie(
                    key=settings.admin_login,
                    value=access_token,
                    httponly=True
                )

                return resp
            else:
                flash(request, "You're not allowed to access this panel", "danger")

                return RedirectResponse(url='/administrator/login/',
                                        status_code=status.HTTP_302_FOUND)

        else:
            flash(request, "Unauthorized Access", "danger")
            resp = RedirectResponse(url='/administrator/login/',
                                    status_code=status.HTTP_302_FOUND)
            resp.delete_cookie(key=settings.admin_login)
            return resp
    except Exception as ex:
        flash(request, str(ex), "danger")
        resp = RedirectResponse(url='/administrator/login/',
                                status_code=status.HTTP_302_FOUND)
        resp.delete_cookie(key=settings.admin_login)
        return resp


@router.get('/administrator/login/')
async def index(request: Request):
    return templates.TemplateResponse('login.html', context={
        'request': request,
        'app_url': app_url
    })


@router.get('/admin/')
async def index(request: Request, user=Depends(get_current_user)):
    try:
        if not await check_login_auth():
            flash(request, "Unauthorized Access", "danger")
            return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
        else:
            if user is None:
                return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)

            course_count = await Course.all().count()
            student_count = await Student.all().count()
            enquiries_count = await StudentEnquiry.all().count()
            course_order = await PaymentRecords.all().count()
            return templates.TemplateResponse('dashboard.html', context={
                'request': request,
                'course_count': course_count,
                'student_count': student_count,
                'enquiries_count': enquiries_count,
                'course_order': course_order,
                'app_url': app_url,
                'ws_url': settings.ws_url,
                'admin_active': 'active',
            })
    except Exception as ex:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)

"""New code added"""

StringId = NewType('StringId', str)


class Cat(BaseModel):
    category: str


"""" New code ended"""


@router.get("/admin/create_course/",)
async def get_course_page(request: Request, user=Depends(get_current_user)):
    try:
        if await check_login_auth():
            if user is None:
                return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
            app_url = db_config().app_url
            pref_obj = await Preference_Pydantic.from_queryset(Preference.all())
            course_obj = await Course_Pydantic.from_queryset(Course.all())
            category_obj = await Category_Pydantic.from_queryset(Category.all())
            topic_obj = await Topics_Pydantic.from_queryset(Topics.all())

            # return category_obj

            return templates.TemplateResponse('create_course.html', context={
                'request': request,
                'pref_names': pref_obj,
                'courses': course_obj,
                'categories': category_obj,
                'topics': topic_obj,
                'app_url': app_url,
                'create_order_active': 'active',
            })
    except Exception as ex:
        # return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)


@router.post("/add_preference")
async def add_preference(request: Request, pref_name: str = Form(...), user=Depends(get_current_user)):
    if await check_login_auth():
        if user is None:
            return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
        res = await Preference.create(
            name=pref_name, slug=slugify(pref_name),
            updated_at=updated_at, created_at=updated_at
        )
        return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)


# """ Upload Image to S3"""


async def upload_images(s3, folder, image: UploadFile, mimetype, user=Depends(get_current_user)):
    dt = datetime.now()
    image_name = (image.filename).split('.')
    ts = datetime.timestamp(dt)
    new_image_name = image_name[0]+'_'+str(ts)+'.'+image_name[1]
    upload_obj = upload_file_to_bucket(s3_client=s3, file_obj=image.file,
                                       bucket='testing-bucket-s3-uploader',
                                       folder=folder,
                                       mimetype=mimetype,
                                       object_name=new_image_name
                                       )
    if upload_obj:
        imagekit_url = imagekit.url({
            "path": "/" + folder + "/" + new_image_name,
            "url_endpoint": "https://ik.imagekit.io/imagnus/",
            "transformation": [{"height": "300", "width": "400"}],
        })
        imagekit_url = imagekit_url.split("?")
        new_url = imagekit_url[0]
        # new_url = "https://d11qyj7iojumc4.cloudfront.net/" + folder + "/" + image.filename
    else:
        imagekit_url = None
        new_url = None
    return new_url


async def upload_pdf_notes(s3, folder, image: UploadFile, mimetype, user=Depends(get_current_user)):
    upload_obj = upload_file_to_bucket(s3_client=s3, file_obj=image.file,
                                       bucket='testing-bucket-s3-uploader',
                                       folder=folder,
                                       mimetype=mimetype,
                                       object_name=image.filename
                                       )
    if upload_obj:
        imagekit_url = imagekit.url({
            "path": "/" + folder + "/" + image.filename,
            "url_endpoint": "https://ik.imagekit.io/imagnus/",
            # "transformation": [{"height": "300", "width": "400"}],
        })
        imagekit_url = imagekit_url.split("?")
        new_url = imagekit_url[0]
        # new_url = "https://d11qyj7iojumc4.cloudfront.net/" + folder + "/" + image.filename
    else:
        imagekit_url = None
        new_url = None
    return new_url


@router.post('/create_course', )
async def create_course(request: Request, pref_id: str = Form(...),
                        name: str = Form(...), icon_image=File(...),
                        web_icon: UploadFile = File(default=None),
                        s3: BaseClient = Depends(s3_auth), user=Depends(get_current_user)):
    try:
        if await check_login_auth():
            if user is None:
                return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
            preference = await Preference.get(id=pref_id)
            image_url = await upload_images(s3, folder='course_icons/mobile_icons', image=icon_image, mimetype=None)
            web_image_url = await upload_images(s3, folder='course_icons/web_icons', image=web_icon, mimetype=None)
            await Course.create(preference=preference, name=name, slug=slugify(name),
                                icon_image=image_url, web_icon=web_image_url, updated_at=updated_at,
                                created_at=updated_at)
            return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


# add category


@router.post("/add_category")
async def add_category(s3: BaseClient = Depends(s3_auth), cat_name: str = Form(...),
                       icon_image: UploadFile = File(...), user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    image_url = await upload_images(s3, folder='category_icons', image=icon_image, mimetype=None)
    await Category.create(name=cat_name, slug=slugify(cat_name), icon_image=image_url, updated_at=updated_at,
                          created_at=updated_at)
    return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)


# edit course
@router.post("/edit_course")
async def edit_course(s3: BaseClient = Depends(s3_auth), edit_name: str = Form(default=None),
                      edit_icon_image: UploadFile = File(default=None),
                      edit_web_icon: UploadFile = File(default=None),
                      edit_course_id: str = Form(...), 
                      edit_telegram_link: str = Form(default=None), 
                      user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    c_instance = await Course.get(id=edit_course_id)
    if edit_course_id:

        if edit_name:
            c_instance.name = edit_name
            # c_instance.slug = slugify(edit_name)

        if edit_icon_image.filename:
            image_url = await upload_images(s3, folder='course_icons/mobile_icons', image=edit_icon_image, mimetype=None)
            c_instance.icon_image = image_url

        if edit_web_icon.filename:
            web_image_url = await upload_images(s3, folder='course_icons/web_icons', image=edit_web_icon, mimetype=None)
            c_instance.web_icon = web_image_url
        
        if edit_telegram_link:
            c_instance.telegram_link = edit_telegram_link
    c_instance.updated_at = updated_at
    await c_instance.save()

    return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)


# edit category

@router.post("/edit_category")
async def edit_category(s3: BaseClient = Depends(s3_auth), cat_name: str = Form(default=None),
                        icon_image: UploadFile = File(default=None), edit_cat_id: str = Form(...),
                        user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    cat_instance = await Category.get(id=edit_cat_id)
    if icon_image or cat_name:
        if edit_cat_id:

            if icon_image.filename:
                image_url = await upload_images(s3, folder='category_icons', image=icon_image, mimetype=None)
                cat_instance.icon_image = image_url

            if cat_name:
                cat_instance.name = cat_name
                cat_instance.slug = slugify(cat_name)

        cat_instance.updated_at = updated_at
        await cat_instance.save()
    return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)

    # return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/course_category/", )
async def get_category_page(request: Request, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    app_url = db_config().app_url
    course_obj = await Course.all()

    course_cat_obj = await Course_Pydantic.from_queryset(
        Course.all()
    )
    cat_obj = await Category_Pydantic.from_queryset(Category.all().order_by('created_at'))
    # return course_cat_obj
    return templates.TemplateResponse('course_category.html', context={
        'app_url': app_url,
        'request': request,
        'courses': course_obj,
        'course_categories': course_cat_obj,
        'categories': cat_obj,
        'course_category': 'active'
    })


@router.post("/admin/add_category/")
async def add_category(courses: List[str] = Form(...), categories: List[str] = Form(...),
                       user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    for course in courses:
        course = await Course.get(id=course)
        for cat in categories:
            category = await Category.get(id=cat)
            if not await CourseCategories.exists(category=category, course=course):
                obj = await CourseCategories.create(
                    category=category, course=course,
                    updated_at=updated_at, created_at=updated_at
                )

    # return templates.TemplateResponse('create_course.html', context={'request': request, 'pref_names': get_obj})
    return RedirectResponse(url='/admin/course_category/', status_code=status.HTTP_303_SEE_OTHER)


'''add subjects'''


@router.post("/add_subject")
async def add_preference(subject_name: str = Form(...), user=Depends(get_current_user)):
    if not await subjects.exists(name=subject_name):
        res = await subjects.create(name=subject_name, slug=slugify(subject_name))
        return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)


@router.get('/admin/chapters/{course}/{category}/')
async def chapters(request: Request, course: str, category: str, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    course = await Course.get(slug=course)
    category = await Category.get(slug=category)
    cat_list = await CourseCategories_Pydantic.from_queryset(
        CourseCategories.filter(course=course, category=category).order_by('created_at'))
    topic_obj = await Topics_Pydantic.from_queryset(Topics.filter(category=category))
    course_category_obj = await CourseCategories.get(id=cat_list[0].id)
    course_category_topic_obj = await CategoryTopics_Pydantic.from_queryset(
        CategoryTopics.filter(category=course_category_obj).order_by('order_seq'))
    # return course_category_topic_obj
    return templates.TemplateResponse('category_chapters.html', context={'request': request,
                                                                         'course_category_id': cat_list[0].id,
                                                                         'course': course,
                                                                         'category': category,
                                                                         'topics': topic_obj,
                                                                         'course_category_topics': course_category_topic_obj

                                                                         })


@router.post('/admin/edit_category_topic_titles/{course}/{category}/')
async def edit_category_topic(course: str, category: str, edit_ctid: str = Form(...),
                              title: str = Form(default=None),
                              display_order_no: int = Form(...), user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    instance = await CategoryTopics.get(id=edit_ctid)
    instance.order_seq = display_order_no
    if title is not None:
        topic_instance = await Topics.get(id=title)
        instance.topic = topic_instance
    await instance.save()

    return RedirectResponse(url='/admin/chapters/' + course + '/' + category + '/',
                            status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/topics/")
async def add_category(topic_cat_id: str = Form(...), cat_topic_title: str = Form(...), user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    category = await Category.get(id=topic_cat_id)
    titles = cat_topic_title.split('|')
    for title in titles:
        slug=slugify(title)
        if not await Topics.exists(category=category, slug=slug):
            obj = await Topics.create(
                category=category, name=title, slug=slugify(title),
                updated_at=updated_at, created_at=updated_at
            )
    return RedirectResponse(url='/admin/create_course/', status_code=status.HTTP_303_SEE_OTHER)


# @router.delete("/topics/", response_model=Status, responses={404: {"model": HTTPNotFoundError}})
# async def delete_topics(user=Depends(get_current_user)):
#     deleted_count = await Topics.all().delete()
#     if not deleted_count:
#         raise HTTPException(status_code=208, detail=f"Topic id not found")
#     return Status(message=f"Deleted ")


@router.post('/add_lectures_titles/')
async def add_lectures(course_category: str = Form(...), title: str = Form(...),
                       topic_course: str = Form(...), topic_category: str = Form(...), user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    course_category_obj = await CourseCategories.get(id=course_category)
    topic_obj = await Topics.get(id=title)
    course_obj = await Course.get(id=topic_course)
    category_obj = await Category.get(id=topic_category)
    if not await CategoryTopics.exists(category=course_category_obj, topic=topic_obj):
        await CategoryTopics.create(category=course_category_obj, topic=topic_obj,
                                    updated_at=updated_at, created_at=updated_at)
    return RedirectResponse(url='/admin/chapters/' + course_obj.slug + '/' + category_obj.slug + '/',
                            status_code=status.HTTP_303_SEE_OTHER)


@router.post('/admin/add_category_lecture/')
async def add_category_lecture(course_id: str = Form(...),
                               category_id: str = Form(...),
                               topic_id: str = Form(...), course_topic_id: str = Form(...),
                               lecture_title: str = Form(...), lecture_link: UploadFile = File(...),
                               video_description: str = Form(...),
                               video_thumbnail=File(...), s3: BaseClient = Depends(s3_auth),
                               ):
    lecture_title = lecture_title
    slug = slugify(lecture_title)

    discription = video_description
    course_obj = await Course.get(id=course_id)
    category_obj = await Category.get(id=category_id)
    topic_obj = await Topics.get(id=topic_id)
    category_topic_obj = await CategoryTopics.get(id=course_topic_id)
    topic_name = slugify(topic_obj.name)
    try:
        # media_info = MediaInfo.parse(lecture_link.file)
        # # duration in milliseconds
        # duration_in_ms = media_info.tracks[0].duration
        # duration_in_m = round((duration_in_ms / 1000) / 60, 2)

        url = "http://video.bunnycdn.com/library/" + bunny_library_id + "/videos"
        payload = "{\"title\":\" " + topic_name + "|" + slug + "\"}"
        headers = {
            "Content-Type": "application/*+json",
            "AccessKey": bunny_access_key
        }
        response = requests.request("POST", url, data=payload, headers=headers)
        json_arr = json.loads(response.text)
        guid = json_arr['guid']
        url = "http://video.bunnycdn.com/library/" + \
            bunny_library_id + "/videos/" + guid
        response = requests.request(
            "PUT", url, headers=headers, data=lecture_link.file)
        stat = json.loads(response.text)
        with open('exams_imagnus_error_log.txt', 'a') as the_file:
            the_file.write(str(updated_at) + ' | ' + str(response.text) + '\n')
        # if guid:
        if stat['success']:
            mobile_video_url = "https://" + bunny_host + "/" + guid + "/playlist.m3u8"
            web_video_url = "https://iframe.mediadelivery.net/embed/" + \
                            bunny_library_id + "/" + guid + "?autoplay=false"
            app_thumbnail = await upload_images(s3,
                                                folder='videothumbnails/' + category_obj.slug + '/' + topic_obj.slug,
                                                image=video_thumbnail, mimetype=None)
            n_url = app_thumbnail
            new_url = "https://ik.imagekit.io/imagnus/videothumbnails/" + \
                category_obj.slug+"/"+topic_obj.slug + \
                "/tr:w-300,h-160,fo-auto/"+n_url.split('/')[-1]

            await CourseCategoryLectures.create(title=lecture_title, slug=slug,
                                                app_thumbnail=new_url,
                                                mobile_video_url=mobile_video_url,
                                                web_video_url=web_video_url,
                                                library_id=bunny_library_id,
                                                video_id=guid,
                                                video_duration=0,
                                                discription=discription,
                                                category_topic=category_topic_obj,
                                                updated_at=updated_at,
                                                created_at=updated_at
                                                )
            # return response.text
            return RedirectResponse(
                url='/admin/category_lectures/' + course_obj.slug +
                    '/' + category_obj.slug + '/' + topic_obj.slug + '/',
                status_code=status.HTTP_303_SEE_OTHER)
        else:
            raise HTTPException(status_code=208, detail="Something went wrong")
    except Exception as ex:

        with open('exams_imagnus_error_log.txt', 'a') as the_file:
            the_file.write(str(updated_at) + ' | ' + str(ex) + '\n')

        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)

        # return ex
        # return RedirectResponse(
        #     url='/admin/category_lectures/' + course_obj.slug + '/' + category_obj.slug + '/' + topic_obj.slug + '/',
        #     status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/category_lectures/{course_slug}/{category_slug}/{topic_slug}/", )
async def get_category_lectures(request: Request, course_slug: str, category_slug: str, topic_slug: str,
                                user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)

    if request.session:
        message = request.session['data']
    else:
        message = ''
    request.session.clear()

    course = await Course.get(slug=course_slug)
    category = await Category.get(slug=category_slug)
    topic_obj = await Topics.get(category__slug=category_slug, slug=topic_slug)
    # return topic_obj

    # cat_list = await CourseCategories_Pydantic.from_queryset(CourseCategories.filter(course=course, category=category))
    course_category_obj = await CourseCategories.get(course__slug=course_slug, category__slug=category_slug)

    # course_category_obj = await CourseCategories.get(id=cat_list[0].id)
    # category_topic_id = await CategoryTopics.filter(category=course_category_obj, topic=topic_obj)
    category_topic_obj = await CategoryTopics.get(category__course__slug=course_slug,
                                                  category__category__slug=category_slug, topic=topic_obj)

    lecture_obj = await CourseCategoryLectures_Pydantic.from_queryset(
        CourseCategoryLectures.filter(category_topic=category_topic_obj).order_by('order_display'))

    notes_obj = await CourseCategoryNotes_Pydantic.from_queryset(
        CourseCategoryNotes.filter(category_topic=category_topic_obj).order_by('created_at'))

    test_series = await CourseCategoryTestSeries_Pydantic.from_queryset(
        CourseCategoryTestSeries.filter(category_topic=category_topic_obj).order_by('created_at'))

    # existing_category_courses = await CourseCategories_Pydantic.from_queryset(CourseCategories.all().order_by('created_at'))
    existing_category_courses = await Course.all()
    # return existing_category_courses
    response = templates.TemplateResponse('course_addcategory.html',
                                          context={'request': request,
                                                   'course_category_id': course_category_obj.id,
                                                   'course': course,
                                                   'category': category,
                                                   'lectures': lecture_obj,
                                                   'notes': notes_obj,
                                                   'test_series': test_series,
                                                   'course_topic_id': category_topic_obj.id,
                                                   'topic': topic_obj,
                                                   'existed_courses': existing_category_courses,
                                                   'error_message': message,
                                                   })

    return response


class CategoryPydantic(BaseModel):
    id: uuid.UUID
    name: str


class CourseCategoriesPydantic(BaseModel):
    category: CategoryPydantic

    class Config:
        orm_mode = True


'''fetch the existing topics of the courses'''


@router.post('/admin/get_existing_course_categories/', response_model=List[CourseCategoriesPydantic])
async def get_existing_course(request: Request, user=Depends(get_current_user)):
    data = await request.json()
    existing_courses_category = await CourseCategories_Pydantic.from_queryset(
        CourseCategories.filter(course__id=data['course_id'])
    )
    return existing_courses_category


@router.post('/admin/get_existing_lecture_topics/')
async def get_existing_topics(request: Request):
    data = await request.json()
    category_topic_obj = await CategoryTopics_Pydantic.from_queryset(CategoryTopics.filter(
        category__course__id=data['course_id'], category__category__id=data['category_id']))
    return category_topic_obj


@router.post('/admin/get_existing_lectures/')
async def get_existing_lectures(request: Request):
    data = await request.json()

    categoryTopicinstance = await CategoryTopics.get(
        category__course__id=data['course_id'], category__category__id=data['category_id'],
        topic__id=data['topic_id'])

    lecture_obj = await CourseCategoryLectures_Pydantic.from_queryset(
        CourseCategoryLectures.filter(category_topic=categoryTopicinstance))

    return lecture_obj


@router.post('/admin/add_from_existing_category_lectures/')
async def add_from_existing_video(request: Request, course_id: str = Form(...),
                                  existing_course_category: str = Form(...), topic_id: str = Form(...),
                                  category_id: str = Form(...), course_topic_id: str = Form(...),
                                  lecture_title: str = Form(...), video_description: str = Form(...),
                                  existing_courses: str = Form(...), exiting_category_topics: str = Form(...),
                                  exiting_category_topics_lectures: str = Form(
                                      ...),
                                  video_thumbnail=File(...), s3: BaseClient = Depends(s3_auth),
                                  ):
    global category_obj, course_obj, topic_obj, category_obj
    try:
        course_obj = await Course.get(id=course_id)
        category_obj = await Category.get(id=category_id)
        topic_obj = await Topics.get(id=topic_id)
        category_topic_obj = await CategoryTopics.get(id=course_topic_id)
        # existed_category_topic_obj = await CategoryTopics.get(
        #     category__course__id=existing_courses, category__category__id=existing_course_category,
        #     topic__id=exiting_category_topics)

        lecture_instance = await CourseCategoryLectures.get(id=exiting_category_topics_lectures)

        web_url = lecture_instance.web_video_url
        mobile_url = lecture_instance.mobile_video_url
        library_id = lecture_instance.library_id
        video_id = lecture_instance.video_id
        video_duration = lecture_instance.video_duration

        app_thumbnail = await upload_images(s3, folder='videothumbnails/' + category_obj.slug + '/' + topic_obj.slug,
                                            image=video_thumbnail, mimetype=None)

        await CourseCategoryLectures.create(title=lecture_title, slug=slugify(lecture_title),
                                            app_thumbnail=app_thumbnail,
                                            mobile_video_url=mobile_url,
                                            web_video_url=web_url,
                                            library_id=bunny_library_id,
                                            video_id=video_id,
                                            video_duration=video_duration,
                                            discription=video_description,
                                            category_topic=category_topic_obj,
                                            updated_at=updated_at, created_at=updated_at
                                            )
        return RedirectResponse(
            url='/admin/category_lectures/' + course_obj.slug +
                '/' + category_obj.slug + '/' + topic_obj.slug + '/',
            status_code=status.HTTP_303_SEE_OTHER)

    except Exception as ex:
        request.session['data'] = str(ex)
        # raise HTTPException(status_code=208, detail=ex)
        # return ex
        return RedirectResponse(
            url='/admin/category_lectures/' + course_obj.slug +
                '/' + category_obj.slug + '/' + topic_obj.slug + '/',
            status_code=status.HTTP_303_SEE_OTHER)


'''edit lectures'''


async def call_api(id):
    '''' get the content of current upload'''
    requested_url = "{app_url}/get_uploaded_content/{id}/"

    async with httpx.AsyncClient() as client:
        content_obj = await client.get(requested_url)

        if content_obj.status_code == 200:
            return content_obj.json()


@router.get('/get_uploaded_content/video/{content_id}/',
            response_model=List[PushNotificationsLecturesPydantic]
            )
async def get_uploaded_video_content(content_id: str):
    try:
        list_array = await CourseCategoryLectures_Pydantic.from_queryset(
            CourseCategoryLectures.filter(id=content_id))

        # new_cat_list.append(list_array)

        return list_array
        # return list_array
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/get_uploaded_content/notes/{content_id}/',
            response_model=List[PNeachNotePydantic]
            )
async def get_uploaded_notes_content(content_id: str):
    try:
        list_array = await CourseCategoryNotes_Pydantic.from_queryset(
            CourseCategoryNotes.filter(id=content_id))
        # new_cat_list.append(list_array)

        return list_array
        # return list_array
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/get_uploaded_content/testseries/{content_id}/',
            response_model=List[PNeachNewtestSeriesPydantic]
            )
async def get_uploaded_testseries_content(content_id: str):
    try:

        list_array = await CourseCategoryTestSeries_Pydantic.from_queryset(
            CourseCategoryTestSeries.filter(id=content_id))
        # new_cat_list.append(list_array)

        return list_array
        # return list_array
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/get_uploaded_content/live/{content_id}/',
            response_model=List[eachNewtestSeriesPydantic]
            )
async def get_uploaded_live_content(content_id: str):
    try:

        list_array = await LiveClasses_Pydantic.from_queryset(
            LiveClasses.filter(id=content_id))
        # new_cat_list.append(list_array)

        return list_array
        # return list_array
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


async def fire_push_notification(course_obj, category_obj, topic_obj, saved_obj, title, message):
    ''''Fire a push notification'''
    now = datetime.today()
    # expiry_date__lte = now
    # .values("student__fcm_token")
    fcm_list = await StudentChoices.filter(course=course_obj, expiry_date__gte=now).values("student__fcm_token")
    fcms = list(map(lambda x: x['student__fcm_token'], fcm_list))
    new_list = list(filter(None, fcms))
    course_name = course_obj.name
    if message != 'live':
        category_name = category_obj.name
        topic_name = topic_obj.name
    # registration_ids = [
    #     "cg8qvl2dT-22NhhHwqO3ve:REDACTED_FCM_TOKEN"]

    registration_ids = new_list
    message_icon = "https://exams.imagnus.in/static/courses_assets/css/fonts/ic_launcher.png"
    if message == 'video':
        message_title = "New Lecture Added"
        requested_url = str(app_url) + \
            "/get_uploaded_content/video/" + str(saved_obj) + "/"
    elif message == 'notes':
        message_title = "New Notes Added"
        requested_url = str(app_url) + \
            "/get_uploaded_content/notes/" + str(saved_obj) + "/"
    elif message == 'testseries':
        message_title = "New Testseries Added"
        requested_url = str(app_url) + \
            "/get_uploaded_content/testseries/" + str(saved_obj) + "/"
    elif message == 'live':
        message_title = "Live class scheduled"
        requested_url = str(app_url) + \
            "/api/student/get_live_classes/" + str(course_obj.slug) + "/"

    # if message == 'notes':
    #     for eachFcm in registration_ids:
    #         student_instance = await Student.get(id=)

    async with httpx.AsyncClient() as client:
        content_obj = await client.get(requested_url)
        new_dict = content_obj.json()

        extra_notification_kwargs = {
            "open": message,
            "data_payload": new_dict[0]
        }
        # if message == 'live':
        #    extra_notification_kwargs = new_dict
        # else:
        #     extra_notification_kwargs = new_dict[0]

        if message == 'video':
            message = 'video lecture'

        if message != 'live':

            data_message = "Dear Student New " + message + " has been added for " + course_name + "\n" + \
                           "Category: " + category_name + "\n" + \
                           "Topic:  " + topic_name + "\n" + \
                           "Lecture Name: " + title + "\n\n" + \
                           "Happy learning 👍"

        else:

            data_message = "Dear Student New " + message + " class has been scheduled for " + course_name + "\n" + \
                           "Lecture Name: " + title + "\n\n" + \
                           "Happy learning 👍"

        result = push_service.notify_multiple_devices(
            registration_ids=registration_ids,
            message_icon="app_icon",
            message_title=message_title,
            message_body=data_message,
            click_action="FLUTTER_NOTIFICATION_CLICK",
            data_message=extra_notification_kwargs,
        )
        return True


@router.get('/send_repeated_notifications/{course}/{category}/{topic}/{source}/{lec_id}/{title}/')
async def send_repeated_notifications(course: str, category: str, topic: str, source: str, lec_id: str, title: str):
    course_obj = await Course.get(id=course)

    topic_obj = None
    if await Topics.exists(id=topic):
        topic_obj = await Topics.get(id=topic)
    category_obj = None
    message = source
    if source == 'video':
        if await Category.exists(id=category):
            category_obj = await Category.get(id=category)
        else:
            category_obj = None
    await fire_push_notification(course_obj, category_obj,
                                 topic_obj, lec_id, title, message)

    return {'status': True}


@router.post('/admin/add_category_lecture1/')
async def add_category_lecture(request: Request, course_id: str = Form(...),
                               category_id: str = Form(...),
                               topic_id: str = Form(...), course_topic_id: str = Form(...),
                               lecture_title: str = Form(...), mobile_video_url: str = Form(...),
                               web_video_url: str = Form(...), video_description: str = Form(...),
                               video_thumbnail=File(...), s3: BaseClient = Depends(s3_auth),
                               ):
    course_obj = await Course.get(id=course_id)
    category_obj = await Category.get(id=category_id)
    topic_obj = await Topics.get(id=topic_id)
    category_topic_obj = await CategoryTopics.get(id=course_topic_id)
    try:
        video_duration = 0
        video_id = None
        if 'vimeo' in mobile_video_url:

            video_id_query = mobile_video_url.split('/')[-1]
            video_id = video_id_query.split('.')[0]

            # """Fetch a video details"""
            requested_url = "https://api.vimeo.com/videos/" + video_id

            headers = {'Authorization': 'bearer REDACTED_TOKEN',
                       'Content-Type': 'application/json',
                       'Accept': 'application/vnd.vimeo.*+json;version=3.4'}

            async with httpx.AsyncClient(headers=headers) as client:
                video_content_obj = await client.get(requested_url)
                # video_obj = video_content_obj.json()
                resp = json.loads(video_content_obj.text)

                video_duration = resp['duration']
        app_thumbnail = await upload_images(s3, folder='videothumbnails/' + category_obj.slug + '/' + topic_obj.slug,
                                            image=video_thumbnail, mimetype=None)

        n_url = app_thumbnail
        new_url = "https://ik.imagekit.io/imagnus/videothumbnails/" + \
            category_obj.slug+"/"+topic_obj.slug + \
            "/tr:w-300,h-160,fo-auto/"+n_url.split('/')[-1]

        saved_obj = await CourseCategoryLectures.create(
            title=lecture_title, slug=slugify(lecture_title),
            app_thumbnail=new_url,
            mobile_video_url=mobile_video_url,
            web_video_url=web_video_url,
            library_id=bunny_library_id,
            video_id=video_id,
            video_duration=video_duration,
            discription=video_description,
            category_topic=category_topic_obj,
            updated_at=updated_at,
            created_at=updated_at
        )

        '''send notifications on new upload of video'''
        if saved_obj:
            message = "video"
            await fire_push_notification(course_obj, category_obj,
                                         topic_obj, saved_obj.id, lecture_title, message)

        # return response.text
        return RedirectResponse(
            url='/admin/category_lectures/' + course_obj.slug +
                '/' + category_obj.slug + '/' + topic_obj.slug + '/',
            status_code=status.HTTP_303_SEE_OTHER)

    except Exception as ex:
        raise HTTPException(status_code=208, detail=ex)
        # return ex
        # return RedirectResponse(
        #     url='/admin/category_lectures/' + course_obj.slug +
        #         '/' + category_obj.slug + '/' + topic_obj.slug + '/',
        #     status_code=status.HTTP_303_SEE_OTHER)


@router.post('/admin/edit_category_lecture/')
async def edit_lectures(request: Request, edit_lid: str = Form(...), course_id: str = Form(...), category_id: str = Form(...),
                        order_display: int = Form(...),
                        topic_id: str = Form(...), lecture_title: str = Form(...), video_description: str = Form(...),
                        edit_lecture_web_url: str = Form(...),
                        video_thumbnail: Optional[UploadFile] = File(
                            default=None, media_type='image/*'),
                        edit_mobile_video_url: str = Form(...),
                        video_thumbnail_url: str = Form(...), s3: BaseClient = Depends(s3_auth),
                        ):
    try:
        video_duration = 0
        video_id = None
        if 'vimeo' in edit_mobile_video_url:

            video_id_query = edit_mobile_video_url.split('/')[-1]
            video_id = video_id_query.split('.')[0]

            # """Fetch a video details"""
            requested_url = "https://api.vimeo.com/videos/" + video_id

            headers = {'Authorization': 'bearer REDACTED_TOKEN',
                       'Content-Type': 'application/json',
                       'Accept': 'application/vnd.vimeo.*+json;version=3.4'}

            async with httpx.AsyncClient(headers=headers) as client:
                video_content_obj = await client.get(requested_url)
                # video_obj = video_content_obj.json()
                resp = json.loads(video_content_obj.text)

                video_duration = resp['duration']

        course_obj = await Course.get(id=course_id)
        category_obj = await Category.get(id=category_id)
        topic_obj = await Topics.get(id=topic_id)
        if await CourseCategoryLectures.exists(id=edit_lid):

            instance = await CourseCategoryLectures.get(id=edit_lid)

            instance.title = lecture_title
            instance.discription = video_description
            instance.order_display = order_display
            instance.web_video_url = edit_lecture_web_url
            instance.mobile_video_url = edit_mobile_video_url
            instance.video_id = video_id
            instance.video_duration = video_duration
            if video_thumbnail.filename:
                app_thumbnail = await upload_images(s3,
                                                    folder='videothumbnails/' + category_obj.slug + '/' + topic_obj.slug,
                                                    image=video_thumbnail, mimetype=None)
                n_url = app_thumbnail
                new_url = "https://ik.imagekit.io/imagnus/videothumbnails/" + \
                    category_obj.slug+"/"+topic_obj.slug + \
                    "/tr:w-300,h-160,fo-auto/"+n_url.split('/')[-1]
                instance.app_thumbnail = new_url
            else:
                instance.app_thumbnail = video_thumbnail_url
            instance.updated_at = updated_at

            await instance.save()

            return RedirectResponse(
                url='/admin/category_lectures/' + course_obj.slug +
                    '/' + category_obj.slug + '/' + topic_obj.slug + '/',
                status_code=status.HTTP_303_SEE_OTHER)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


'''Add notes here'''


@router.post('/admin/add_category_notes/')
async def add_category_notes(course_id: str = Form(...), category_id: str = Form(...),
                             topic_id: str = Form(...), course_topic_id: str = Form(...),
                             notes_title: str = Form(...), lecture_note=File(...),
                             notes_thumbnail: UploadFile = File(...), s3: BaseClient = Depends(s3_auth), ):
    course_obj = await Course.get(id=course_id)
    category_obj = await Category.get(id=category_id)
    topic_obj = await Topics.get(id=topic_id)
    category_topic_obj = await CategoryTopics.get(id=course_topic_id)
    if lecture_note.filename:
        folder = 'Notes' + '/' + course_obj.slug + '/' + \
                 category_obj.slug + '/' + topic_obj.slug + \
            '/' + slugify(notes_title)
        image_url = await upload_pdf_notes(s3, folder=folder, image=lecture_note, mimetype='application/pdf')

        folder = 'NotesThumbnail' + '/' + course_id + '/' + \
                 category_id + '/' + topic_id + '/' + slugify(notes_title)
        thumbnail_url = await upload_images(s3, folder=folder, image=notes_thumbnail, mimetype=None)
    else:
        image_url = None
        thumbnail_url = None
    saved_obj = await CourseCategoryNotes.create(title=notes_title, slug=slugify(notes_title),
                                                 notes_url=image_url, thumbnail=thumbnail_url,
                                                 category_topic=category_topic_obj, updated_at=updated_at,
                                                 created_at=updated_at)

    '''send notifications on new upload of notes'''
    if saved_obj:
        message = "notes"
        await fire_push_notification(course_obj, category_obj,
                                     topic_obj, saved_obj.id, notes_title, message)

    return RedirectResponse(
        url='/admin/category_lectures/' + course_obj.slug +
            '/' + category_obj.slug + '/' + topic_obj.slug + '/',
        status_code=status.HTTP_303_SEE_OTHER)


"""
Update course subscriptions
"""


@router.put('/admin/update_subscriptions/')
async def update_subscriptions(uid: str, no_of_videos: int, no_of_notes: int, no_of_tests: int):
    if await CourseSubscriptionPlans.exists(id=uid):
        instance = await CourseSubscriptionPlans.get(id=uid)
        instance.no_of_videos = no_of_videos
        instance.no_of_notes = no_of_notes
        instance.no_of_tests = no_of_tests
        instance.updated_at = updated_at
        await instance.save()
        return {"saved"}
    else:
        return {uid + " not found"}


""" Add test series """


@router.post('/admin/add_category_test_series/')
async def add_category_test_series(course_id: str = Form(...),
                                   category_id: str = Form(...),
                                   topic_id: str = Form(...), course_topic_id: str = Form(...),
                                   time_duration: int = Form(...), marks: int = Form(...),
                                   test_series_title: str = Form(...),
                                   test_series_thumbnail: UploadFile = File(
                                       ...),
                                   lecture_test_series: UploadFile = File(...),
                                   s3: BaseClient = Depends(s3_auth),
                                   ):
    course_obj = await Course.get(id=course_id)
    category_obj = await Category.get(id=category_id)
    topic_obj = await Topics.get(id=topic_id)
    category_topic_obj = await CategoryTopics.get(id=course_topic_id)
    series_count = await CourseCategoryTestSeries.filter(
        title=test_series_title).count()
    if series_count == 0:
        data = pd.read_excel(
            lecture_test_series.file.read())  # place "r" before the path string to address special character,
        # such as '\'. Don't forget to put the file name at the end of the path + '.xlsx'

        image_url = await upload_images(s3, folder='testSeriesthumbnails/' + category_obj.slug + '/' + topic_obj.slug,
                                        image=test_series_thumbnail, mimetype=None)
        test_series_instance = await CourseCategoryTestSeries.create(
            category_topic=category_topic_obj, time_duration=time_duration,
            marks=marks, no_of_qstns=len(data), title=test_series_title, thumbnail=image_url,
            updated_at=updated_at, created_at=updated_at
        )

        for i, k in data.iterrows():
            await CourseCategoryTestSeriesQuestions.create(
                question=k['questions'],
                opt_1=k['opt_1'],
                opt_2=k['opt_2'],
                opt_3=k['opt_3'],
                opt_4=k['opt_4'],
                answer=k['answer'],
                solution=k['solution'],
                test_series=test_series_instance
            )

        if test_series_instance:
            message = "testseries"
            await fire_push_notification(course_obj, category_obj,
                                         topic_obj, test_series_instance.id, test_series_title, message)

        return RedirectResponse(
            url='/admin/category_lectures/' + course_obj.slug +
                '/' + category_obj.slug + '/' + topic_obj.slug + '/',
            status_code=status.HTTP_303_SEE_OTHER)

    else:
        return RedirectResponse(
            url='/admin/category_lectures/' + course_obj.slug + '/' +
                category_obj.slug + '/' + topic_obj.slug + '/?m=already exists',
            status_code=status.HTTP_303_SEE_OTHER)


# get all lectures and
"""@router.get('/admin/get_all_lectures')
async def get():
    return await CourseCategoryLectures_Pydantic.from_queryset(CourseCategoryLectures.all())
"""


@router.get('/admin/video_lecture/')
async def video_lecture(request: Request, link: str):
    return templates.TemplateResponse('video_lecture.html', context={'request': request,
                                                                     'link': link
                                                                     })


@router.get('/admin/subscription_plan/')
async def subscription_plan(request: Request, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    plan_obj = await SubscriptionPlans_Pydantic.from_queryset(SubscriptionPlans.all())
    course_obj = await Course_Pydantic.from_queryset(Course.all())
    course_plans = await CourseSubscriptionPlans_Pydantic.from_queryset(CourseSubscriptionPlans.all().order_by('-updated_at'))
    return templates.TemplateResponse('subscription_plan.html', context={'request': request,
                                                                         'plan_obj': plan_obj,
                                                                         'courses': course_obj,
                                                                         'course_plans': course_plans,
                                                                         'subscription_plan_active': 'active',
                                                                         })


@router.post('/admin/add_subscription_plan/')
async def subscription_plan(plan_name: str = Form(...), sub_title: str = Form(...),
                            icon_image: str = Form(...), user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    await SubscriptionPlans.create(
        name=plan_name, sub_title=sub_title, slug=slugify(plan_name), icon_image=icon_image,
        updated_at=updated_at, created_at=updated_at)
    return RedirectResponse(url='/admin/subscription_plan/', status_code=status.HTTP_303_SEE_OTHER)


@router.post('/admin/edit_subscription_plan/')
async def edit_subscription_plan(edit_plan_price: str = Form(...), edit_plan_validity: str = Form(...),
                                 edit_no_of_videos: str = Form(...),
                                 edit_no_of_tests: str = Form(...), edit_no_of_notes: str = Form(...),
                                 edit_sid: str = Form(...), edit_live_classes_access: int = Form(default=0)):
    await CourseSubscriptionPlans.filter(id=edit_sid).update(plan_price=edit_plan_price, validity=edit_plan_validity,
                                                             no_of_videos=edit_no_of_videos,
                                                             no_of_notes=edit_no_of_notes, no_of_tests=edit_no_of_tests,
                                                             live_classes_access=edit_live_classes_access)
    return RedirectResponse(url='/admin/subscription_plan/', status_code=status.HTTP_303_SEE_OTHER)


'''@router.delete('/admin/delete_video_lecture')
async def delete_lectures():
    await CourseCategoryLectures.all().delete()
    return {"deleted"}'''


@router.delete('/admin/delete_video_lecture/{lid}')
async def delete_lectures(lid: str):
    await CourseCategoryLectures.filter(id=lid).delete()
    return {"deleted"}


@router.delete('/admin/delete_notes/{nid}')
async def delete_notes(nid: str):
    await CourseCategoryNotes.filter(id=nid).delete()
    return {"deleted"}


@router.delete('/admin/delete_testseries/{tid}/')
async def delete_testseries(tid: str):
    await CourseCategoryTestSeries.filter(id=tid).delete()
    return {"deleted"}


# @router.delete('/admin/delete_course_subscription_plan/')
# async def delete_course_subscription_plan():
#     await CourseSubscriptionPlans.all().delete()
#     return {"{id} deleted"}


@router.post('/admin/add_course_subscription_plan/')
async def course_subscription_plan(course: str = Form(...), package_name: str = Form(...),
                                   validity: str = Form(...), plan_price: int = Form(...),
                                   discount_plan_price: str = Form(...),
                                   no_of_videos: int = Form(...), no_of_notes: int = Form(...),
                                   no_of_tests: int = Form(...), live_classes_access: bool = Form(default=0)
                                   ):
    course_ins = await Course.get(id=course)
    package_ins = await SubscriptionPlans.get(id=package_name)
    if not await CourseSubscriptionPlans.exists(course=course_ins, SubscriptionPlan=package_ins):
        await CourseSubscriptionPlans.create(course=course_ins, SubscriptionPlan=package_ins, validity=validity,
                                             plan_price=plan_price, discount_price=discount_plan_price,
                                             no_of_videos=no_of_videos, no_of_notes=no_of_notes,
                                             no_of_tests=no_of_tests, live_classes_access=live_classes_access,
                                             updated_at=updated_at, created_at=updated_at)
    return RedirectResponse(url='/admin/subscription_plan/', status_code=status.HTTP_303_SEE_OTHER)


# get all lectures and
@router.get('/admin/student/registrations/')
async def get_students(request: Request, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    students = await Student.all().order_by('-created_at')
    return templates.TemplateResponse('student_registrations.html',
                                      context={'request': request,
                                               'students': students,
                                               'registrations_active': 'active',
                                               })


@router.get('/admin/student_details/{student_id}/')
async def get_students(request: Request, student_id: str):
    student = await Student_Pydantic.from_queryset(Student.filter(id=student_id))
    return templates.TemplateResponse('student_details.html',
                                      context={'request': request,
                                               'student': student[0],
                                               })


"""
Add course overview
"""


@router.get('/admin/course_overview/')
async def get_students(request: Request, user=Depends(get_current_user)):
    course_obj = await Course_Pydantic.from_queryset(Course.all())
    overview_obj = await CourseCategoryOverview_Pydantic.from_queryset(CourseCategoryOverview.all())

    return templates.TemplateResponse('course_overview.html',
                                      context={'request': request,
                                               'courses': course_obj,
                                               'overviews': overview_obj,
                                               'course_overview_active': 'active',
                                               })


@router.post('/admin/add_course_overview/')
async def add_course_overview(course: str = Form(...), overview: str = Form(...),
                              examination: str = Form(...), syllabus: str = Form(...)):
    course_ins = await Course.get(id=course)
    await CourseCategoryOverview.create(course=course_ins, overview=overview, examination=examination,
                                        syllabus=syllabus)
    return RedirectResponse(url='/admin/course_overview/', status_code=status.HTTP_303_SEE_OTHER)


@router.get('/admin/course_overview/')
async def course_overview(request: Request, user=Depends(get_current_user)):
    course_obj = await Course_Pydantic.from_queryset(Course.all())
    overview_obj = await CourseCategoryOverview_Pydantic.from_queryset(CourseCategoryOverview.all())

    return templates.TemplateResponse('course_overview.html',
                                      context={'request': request,
                                               'courses': course_obj,
                                               'overviews': overview_obj,
                                               })


@router.get('/admin/student_enquiries/')
async def add_student_enquiries(request: Request):
    enquiry_obj = await StudentEnquiry_Pydantic.from_queryset(StudentEnquiry.all().order_by("-created_at"))
    return templates.TemplateResponse('student_enquiries.html',
                                      context={'request': request,
                                               'enquiries': enquiry_obj,
                                               'student_enquiries_active': 'active',
                                               })


@router.get('/admin/scholarship/testseries/')
async def scholarship_testseries_page(request: Request):
    test_series = await ScholarshipTestSeries_Pydantic.from_queryset(ScholarshipTestSeries.all())
    return templates.TemplateResponse('scholarship-testseries.html',
                                      context={
                                          'request': request,
                                          'test_series': test_series,
                                          'testseries': 'active',
                                      })


'''Add scholarship test series'''


@router.post('/admin/add/scholarship/testseries/')
async def add_scholarship_testseries(request: Request, on_date: datetime = Form(...), end_date: datetime = Form(...),
                                     time_duration: int = Form(...), total_marks: int = Form(...),
                                     title: str = Form(...),
                                     lang: str = Form(...),
                                     image: UploadFile = File(...),
                                     testseries_file: UploadFile = File(...),
                                     description: str = Form(...),
                                     s3: BaseClient = Depends(s3_auth),
                                     ):
    async def get_localtimezone(dt_params):
        lc_datetime = tz.localize(dt_params)
        new_datetime = lc_datetime.isoformat()

        return new_datetime

    # print(new_datetime)
    data = pd.read_excel(
        testseries_file.file.read())

    await ScholarshipTestSeries.filter(lang=lang).delete()
    folder = 'scholarship/2022/banner_images/'
    image_url = await upload_pdf_notes(s3, folder=folder, image=image, mimetype=None)
    test_series_instance = await ScholarshipTestSeries.create(
        on_date=on_date,
        end_date=end_date,
        image=image_url,
        description=description,
        time_duration=time_duration,
        total_marks=total_marks, no_of_qstns=len(data),
        lang=lang, title=title,
    )

    for i, k in data.iterrows():
        await ScholarshipTestSeriesQuestions.create(
            question=k['questions'],
            opt_1=k['opt_1'],
            opt_2=k['opt_2'],
            opt_3=k['opt_3'],
            opt_4=k['opt_4'],
            answer=k['answer'],

            test_series=test_series_instance
        )

    return RedirectResponse(url='/admin/scholarship/testseries/', status_code=status.HTTP_303_SEE_OTHER)


@router.get('/admin/orders/')
async def get_orders(request: Request, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)

    course_ord_cnt = await PaymentRecords.filter(bill_amount__gt=0).count()
    std_m_count = await StudyMaterialOrderInstance.all().count()
    test_series_count = await TestSeriesOrders.all().count()
    return templates.TemplateResponse('orders.html',
                                      context={
                                          'request': request,
                                          'course_ord_cnt': course_ord_cnt,
                                          'std_m_count': std_m_count,
                                          'test_series_count': test_series_count,
                                          'orders_active': 'active'
                                      })


@router.get('/admin/course_orders/')
async def get_orders(request: Request, page: int = Query(..., title="Page Number", ge=1),
                     perPage: int = Query(...,
                                          title="Data limit per page", ge=0, le=50),
                     user=Depends(get_current_user)
                     ):
    if user is None:
        return RedirectResponse(url="/administrator/login/", status_code=status.HTTP_302_FOUND)
    orders = await PaymentRecords_Pydantic.from_queryset(
        PaymentRecords.all().order_by('-created_at')
        .offset((page*perPage)-perPage)
        .limit(perPage)
    )
    data_count = await PaymentRecords.all().count()
    segments = data_count/perPage
    # return orders
    client_host = request.client.host
    # forwarded_for = context.data["X-Forwarded-For"].split(',')

    return templates.TemplateResponse('course_orders.html',
                                      context={
                                          'request': request,
                                          'orders': orders,
                                          'page_segments': segments,
                                          'page': page,
                                          'perPage': perPage,
                                          'data_count': data_count,
                                          "client_host": client_host,
                                          #   "forwarded_for": forwarded_for[0]
                                      })


@router.get('/admin/study_material_orders/')
async def get_orders(request: Request, page: int = Query(..., title="Page Number", ge=1),
                     perPage: int = Query(...,
                                          title="Data limit per page", ge=0, le=50),
                     user=Depends(get_current_user)):
    orders = await StudyMaterialOrderInstance_Pydantic.from_queryset(
        StudyMaterialOrderInstance.all().order_by('-created_at')
        .offset((page*perPage)-perPage)
        .limit(perPage)
    )
    # return orders
    return templates.TemplateResponse('study_material_orders.html',
                                      context={
                                          'request': request,
                                          'orders': orders,
                                          'page': page,
                                          'perPage': perPage,
                                      })


@router.get('/admin/test_series_orders/')
async def get_orders(request: Request, page: int = Query(..., title="Page Number", ge=1),
                     perPage: int = Query(...,
                                          title="Data limit per page", ge=0, le=50),
                     user=Depends(get_current_user)):
    orders = await TestSeriesOrders_Pydantic.from_queryset(
        TestSeriesOrders.all().order_by('-created_at')
        .offset((page*perPage)-perPage)
        .limit(perPage)
    )
    # orders =  await TestSeriesOrders.all().order_by('-created_at').offset((page*perPage)-perPage).limit(perPage)
    # return jsonable_encoder(orders)
    return templates.TemplateResponse('orders_testseries.html',
                                      context={
                                          'request': request,
                                          'orders': orders,
                                          'page': page,
                                          'perPage': perPage,
                                      })


@router.get('/admin/live_classes/')
async def get_live_classes(request: Request, user=Depends(get_current_user)):
    course_obj = await Course.all()
    instructor_obj = await Instructor.all()
    live_classes = await LiveClasses_Pydantic.from_queryset(
        LiveClasses.all())
    return templates.TemplateResponse('add_live_classes.html', context={
        'request': request,
        'courses': course_obj,
        'live_classes': live_classes,
        'instructors': instructor_obj,
        'live_classes_active': 'active',
    })


@router.post('/admin/add_live_class/')
async def add_live_class(request:Request,course_id: List[str] = Form(...), instructor_id: str = Form(...), mode: str = Form(...),
                         stream_time: datetime = Form(...),
                         title: str = Form(...), thumbnail: UploadFile = File(default=None), url: Optional[str] = Form(default=None),
                         s3: BaseClient = Depends(s3_auth), user=Depends(get_current_user)):
  try:
    for cid in course_id:
        course = await Course.get(id=cid)
        instructor = await Instructor.get(id=instructor_id)
        image_url = None
        if thumbnail.filename:
            image_url = await upload_images(s3, folder='live_classes/thumbnails', image=thumbnail, mimetype=None)
        if mode == '1':
            is_paid = True
        else:
            is_paid = False
        if app_url == 'https://exams.imagnus.in':
            lecture_id = 'da9f64de-95cb-4349-91b1-f5c78c7abfe1'
        elif app_url == 'https://testserver.imagnus.in':
            lecture_id = '1302e05b-46b3-4a19-ac31-5f1ea279a7d9'
        elif app_url == 'http://127.0.0.1:8000':
            lecture_id = '3645de71-2140-4a43-9005-3cb0141004ed'
        lecture = await CourseCategoryLectures.get(id=lecture_id)
        saved_obj = await LiveClasses.create(title=title, course=course, streaming_time=stream_time, lecture=lecture,
                                             instructor=instructor, thumbnail=image_url, url=url, is_paid=is_paid, )

        if saved_obj:
            message = "live"
            category_obj = ""
            topic_obj = ""
            await fire_push_notification(course, category_obj,
                                         topic_obj, saved_obj.id, title, message)

    return RedirectResponse(url='/admin/live_classes/', status_code=status.HTTP_303_SEE_OTHER)


  except Exception as ex:
          flash(request, str(ex), "danger")
          return RedirectResponse(url='/admin/live_classes/', status_code=status.HTTP_303_SEE_OTHER)

    #    return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/admin/edit_live_classes')
async def edit_live_classes(request: Request,edit_live_class_id:str=Form(...),
                            s3: BaseClient = Depends(s3_auth),
                            edit_icon_image:UploadFile = File(default=None), 
                            link_class:str = Form(default=None)):
    if link_class:
        if await LiveClasses.get(id=edit_live_class_id):
             live_class = await LiveClasses.get(id=edit_live_class_id).update(url=link_class)
             
        
    if edit_icon_image.filename:
        image_url = await upload_images(s3, folder='live_classes/thumbnails', image=edit_icon_image, mimetype=None)
        if await LiveClasses.get(id=edit_live_class_id):
            live_class = await LiveClasses.get(id=edit_live_class_id).update(thumbnail=image_url)
    flash(request, "Edit successful", "success")

    return RedirectResponse(url='/admin/live_classes/', status_code=status.HTTP_303_SEE_OTHER)

@router.post('/admin/delete_live_classs/')
async def delete_class(live_class_id: str = Form(...)):
    await LiveClasses.filter(id=live_class_id).delete()
    return RedirectResponse(url='/admin/live_classes/', status_code=status.HTTP_303_SEE_OTHER)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        course_count = await Course.all().count()
        student_count = await Student.all().count()
        enquiries_count = await StudentEnquiry.all().count()
        course_order = await PaymentRecords.all().count()
        array = {
            "course_count": course_count,
            "student_count": student_count,
            "enquiries_count": enquiries_count,
            "course_order": course_order,
        }
        data = json.dumps(array)
        await websocket.send_text(f"{data}")


async def pretty_date(created_at):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    datetime_now = datetime.now(tz)
    diff = datetime_now - created_at
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(round(second_diff)) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(round(second_diff / 60)) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(round(second_diff / 3600)) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(round(day_diff)) + " days ago"
    if day_diff < 31:
        return str(round(day_diff / 7)) + " weeks ago"
    if day_diff < 365:
        return str(round(day_diff / 30)) + " months ago"
    return str(round(day_diff / 365)) + " years ago"


@router.get('/admin/reply_doubts/')
async def reply_doubts(request: Request, user=Depends(get_current_user)):
    try:

        doubts = await Ask.all().order_by('-created_at')
        new_list = []
        for doubt in doubts:
            new_dict = jsonable_encoder(doubt)
            std_obj = await Student.get(id=doubt.student_id)
            new_dict.update({"student_name": std_obj.fullname})
            new_dict.update({"mobile": std_obj.mobile})
            # cr_date = datetime.strptime(
            #     doubt.updated_at, '%a, %B %d, %Y %I:%M:%S %p')
            cr_date = doubt.updated_at.strftime("%a, %B %d, %Y %I:%M:%S %p")
            dated_at = await pretty_date(doubt.created_at)
            new_dict.update({"updated_at": cr_date})
            new_dict.update({"dated_at": dated_at})
            new_list.append(new_dict)
        # return new_list
        return templates.TemplateResponse('reply_to_doubts.html',
                                          context={'request': request,
                                                   'doubts': new_list,
                                                   'registrations_active': 'active',

                                                   })
    except Exception as ex:
        raise HTTPException(detail=str(ex), status_code=208)


@router.post('/admin/update_query_reply/')
async def update_query_reply(request: Request):
    data = await request.json()
    qid = data['qid']
    enquiry = data['reply']
    """
      Add FCM push message for students
    """

    ask_obj = await Ask.get(id=qid).values("student__id")
    student_id = ask_obj["student__id"]
    user_obj = await Student.get(id=student_id)
    obj = await Ask.filter(id=qid).update(reply=enquiry, is_replied=True)
    fcm_token = user_obj.fcm_token
    if fcm_token:
        message_title = 'Query Answered!!!'
        message_body = "Hi " + user_obj.fullname+",\n Your last asked question has been answered.\n\n\
                            Happy Learning"
        data_message = {
            "open": "ask",
            "data_payload": {}
        }
        result = push_service.notify_single_device(registration_id=fcm_token,
                                                   message_title=message_title,
                                                   message_body=message_body,
                                                   data_message=data_message)

    return {'yes'}


@router.post('/update_notes_url/')
async def update_notes_url():
    all_notes = await CourseCategoryLectures.all()
    for idx, notes in enumerate(all_notes):
        uid = notes.id
        n_url = notes.app_thumbnail
        category_topic_id = notes.category_topic_id
        if len(n_url) > 4:
            category_slug_obj = await CategoryTopics.get(id=category_topic_id).values("category__category__slug", "topic__slug")
            category_slug = category_slug_obj["category__category__slug"]
            topic_slug = category_slug_obj["topic__slug"]

        # url_split = n_url.split('/')

            new_url = "https://ik.imagekit.io/imagnus/videothumbnails/" + \
                category_slug+"/"+topic_slug + \
                "/tr:w-300,h-160,fo-auto/"+n_url.split('/')[-1]
            print(new_url)
        #     # new_url = n_url.replace(
        #     #     "d11qyj7iojumc4.cloudfront.net", "ik.imagekit.io/imagnus")

            await CourseCategoryLectures.get(id=uid).update(app_thumbnail=new_url)
            print(idx)
            print("done")

    return {}


@router.get('/admin/student/scholarship/registrations/')
async def get_students(request: Request, user=Depends(get_current_user)):
    students = await Scholarship2021.all().order_by('-created_at')
    return templates.TemplateResponse('scholarship_registrations.html',
                                      context={'request': request,
                                               'students': students,
                                               'scholarship_registrations': 'active',
                                               })


@router.post('/search_order/')
async def search_order(request: Request):
    data = await request.json()

    mobile = data["mobile"]

    if await Student.exists(mobile=mobile):
        
        student = await Student.get(mobile=mobile)
        pay_objs=None
        if data["source"] == 'course_orders':

            student_id = student.id
            if await PaymentRecords.exists(student=student):
                pay_objs = await PaymentRecords.filter(
                    student=student
                ).values("id","student__fullname", "student__mobile",
                         "subscription__course__name",
                         "order_id", "payment_id", "bill_amount",
                         "payment_mode",
                         "payment_status", "source", "created_at"
                         )
        elif data["source"] == 'material_orders':
            pay_objs = await StudyMaterialOrderInstance_Pydantic.from_queryset(
                StudyMaterialOrderInstance.filter(
                    student=student
                )
            )

        elif data["source"] == 'testseries_orders':
            pay_objs = await TestSeriesOrders_Pydantic.from_queryset(
                TestSeriesOrders.filter(
                    student=student
                )
            )

        return JSONResponse({"status": True, "source": data['source'], "message": jsonable_encoder(pay_objs)})


@router.get('/admin/student/interview/registrations/')
async def get_students(request: Request, user=Depends(get_current_user)):
    students = await InterViewProgram.all().order_by('-created_at')
    return templates.TemplateResponse('interview_enquiry.html',
                                      context={'request': request,
                                               'students': students,
                                               'interview_registrations': 'active',
                                               })


@router.get('/update_expiry_date/')
async def add_new_date():
    # stud_obj = await StudentChoices.filter(
    #     course__id__in=[
    #         'eaa1467e-3e01-423b-9bcd-36d7b2cdbe5e']
    # )

    # i = 0
    # for each_obj in stud_obj:
    #     expiry = each_obj.expiry_date
    # #     new_expiry_date = created + relativedelta(years=1)
    # #     updated_at = datetime.now(tz)
    # #     await StudentChoices.filter(id=each_obj.id).update(expiry_date=new_expiry_date, updated_at=updated_at)
    # #     i = i + 1
    # #     print(i)
    #     # if (expiry.month == (11)) & (expiry.year == 2022):  # and exp_date.day <= 15
    #     #     i = i + 1
    #     # # #    new_expiry_date = exp_date + relativedelta(months=2)
    #     #     new_expiry_date = parser.parse('2022-12-01T23:59:59.410158+05:30')
    #     #     await StudentChoices.filter(id=each_obj.id).update(expiry_date=new_expiry_date)
    #     #     print(i)
    return {"done"}


@router.get('/admin/place_order/')
async def create_order(request: Request, user=Depends(get_current_user)):
    courses = await Course.all()
    return templates.TemplateResponse('place_order.html',
                                      context={'request': request,
                                               'courses': courses,
                                               'interview_registrations': 'active',
                                               })


@router.post('/admin/get_course_subscriptions/')
async def get_course_subscriptions(request: Request, user=Depends(get_current_user)):
    try:
        data = await request.json()
        subscriptions = await CourseSubscriptionPlans.filter(course__id=data['course_id'], is_active=True).values(sid="id", name="SubscriptionPlan__name", validity="validity", price="plan_price")
        return subscriptions
    except Exception as ex:
        return JSONResponse({'message': str(ex)})


@router.post('/admin/place_manual_order/')
async def manual_order(request: Request, phone_number: str = Form(...), subscription_id: str = Form(...), discount_price: Optional[int] = Form(default=0)):
    try:
        if not await Student.exists(mobile=phone_number):
            flash(request, "Mobile no. is not registered.", "danger")

            return RedirectResponse(url='/admin/place_order/', status_code=status.HTTP_303_SEE_OTHER)
        student = await Student.get(mobile=phone_number)
        print(subscription_id)
        if not discount_price:
            subscription = await CourseSubscriptionPlans.get(id=subscription_id)
            course_price = subscription.plan_price
        else:
            course_price = discount_price
        params = {
            'username': 'REDACTED_LEGACY_API_USERNAME',
            'password': 'REDACTED_LEGACY_API_PASSWORD'

        }
        order_params = {
            "payment_mode": 1,
            "payment_status": 1,
            "payment_id": "",
            "order_id": "",
            "gateway_name": "",
            "coupon": "",
            "coupon_discount": 0,
            "notes": "Order Placed by Admin",
            "source": "adm",
            "bill_amount": course_price,
            "student_id": student.id,
            "subscription_id": subscription_id

        }

        async with httpx.AsyncClient() as client:
            r = await client.post(app_url+'/api/student/v2/auth/token/', data=params)
            decoded = json.loads(r.text)
            print(decoded['access_token'])
            headers = {'Authorization': 'Bearer '+decoded['access_token']}
            async with httpx.AsyncClient(headers=headers) as client1:
                order_response = await client1.post(app_url+'/api/place_order',
                                                    json=jsonable_encoder(order_params))
                result = json.loads(order_response.text)
                if result['status'] == True:
                    flash(request, "Subscription activated", "success")
                else:
                    flash(request, result['message'], "danger")

            return RedirectResponse(url='/admin/place_order/', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        flash(request, str(e), "danger")
        return RedirectResponse(url='/admin/place_order/', status_code=status.HTTP_303_SEE_OTHER)

        # return JSONResponse({"status": False, "message": str(e)})


@router.get('/admin/get_live_class_schedules/')
async def get_live_class_schedules(request: Request, _=Depends(get_current_user)):
    return templates.TemplateResponse('live_class_time_scheduling.html',
                                      context={'request': request,
                                               'schedule_live_class': 'active',
                                               })


@router.delete('/admin/delete_subscription')
async def delete_subscription(request: Request,_=Depends(get_current_user)):
    data = await request.json()
    if await PaymentRecords.exists(id=data['sid']):
        await PaymentRecords.get(id=data['sid']).delete()
        return JSONResponse({'status': True, 'message':'deletion successful'})
    else:
        return JSONResponse({'status': False, 'message':'something went wrong'})
        
        
@router.get('/admin/current/affairs/') 
async def current_affairs(request: Request, _=Depends(get_current_user)):
    current_affairs = await CurrentAffairs.all().order_by("-created_at")
    
    return templates.TemplateResponse('current_affairs.html',
                                      context={'request': request,
                                               'current_affairs': current_affairs,
                                               })
@router.post('/admin/add/current/affairs/')
async def add_current_affairs(request:Request,day:str = Form(...),month_year:str=Form(...),file: UploadFile = File(...),
                              s3: BaseClient = Depends(s3_auth), user=Depends(get_current_user)):
    if not await CurrentAffairs.exists(day=day,month_year=month_year):
        file_url = await upload_images(s3, folder='current_affairs', image=file, mimetype=None)

        res = await CurrentAffairs.create(day=day,month_year=month_year,file_url=file_url)
        if res:
            flash(request, "Added Successfully.", "success")
            
            return RedirectResponse(url='/admin/current/affairs/', status_code=status.HTTP_303_SEE_OTHER)
        else:
            flash(request, "error occured.", "danger")
            
            return RedirectResponse(url='/admin/current/affairs/', status_code=status.HTTP_303_SEE_OTHER)
        
@router.delete('/admin/delete_current_affairs/',name="delete-current-affairs") 
async def  delete_current_affairs(request:Request, _=Depends(get_current_user)):
    try:
        data = await request.json()
        await CurrentAffairs.get(id=data['sid']).delete()
        return {"status":True,"message": "Record deleted successfully"}      
    except Exception as ex:
        return {"status":False,"message": str(ex)}
    
@router.get('/admin/display-download-video')    
async def display_progress(request: Request, _=Depends(get_current_user)):
    return templates.TemplateResponse('video_download_progress.html', context={
        'request': request,
        'app_url': app_url
    })