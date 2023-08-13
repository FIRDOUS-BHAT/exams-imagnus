from utils.util import dd
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
import numpy as np
import json
import uuid
from datetime import datetime
from datetime import timedelta
from functools import lru_cache
from typing import List, Optional

import pytz
# import jwt
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, Form
from fastapi.encoders import jsonable_encoder
from fastapi.security import APIKeyCookie
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi_login import LoginManager  # Loginmanager Class
from fastapi_login.exceptions import InvalidCredentialsException  # Exception class
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime, timezone
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, RedirectResponse
from tortoise.contrib.fastapi import HTTPNotFoundError

from admin_dashboard.models import CourseCategoryTestSeriesQuestions_Pydantic, LiveClasses, LiveClasses_Pydantic, \
    Preference_Pydantic, Preference, Course, \
    CourseCategories_Pydantic, CourseCategories, \
    CategoryTopics, CourseCategoryLectures, CourseCategoryLectures_Pydantic, Topics, Category, CourseCategoryTestSeries, \
    CourseCategoryTestSeriesQuestions, CourseSubscriptionPlans, CourseCategoryNotes
from checkout.models import PaymentRecords
from configs import appinfo
from send_sms.api import generateOTP, sendSMS
from student.models import Student, StudentTestSeriesRecord, Student_Pydantic, UserToken
from student_choices.models import activeSubscription_Pydantic, studentActivity, activeSubscription, BookMarkedNotes, BookMarkedVideos, studentNotesActivity
from utils import util
from email_validator import validate_email, EmailNotValidError

tz = pytz.timezone('Asia/Kolkata')


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()

app = FastAPI()

cookie_sec = APIKeyCookie(name=settings.cookie_name)

secret_key = settings.secret_key

templates = Jinja2Templates(directory="student/templates")

router = APIRouter()


class Status(BaseModel):
    message: str


SECRET = settings.secret_key
# SECRET = "secret-key"
# To obtain a suitable secret key you can run | import os; print(os.urandom(24).hex())

manager = LoginManager(
    SECRET, token_url="/student/secure_login/", use_cookie=True, use_header=False)
manager.cookie_name = settings.cookie_name


class SessionData(BaseModel):
    message: str


async def get_cookie(request: Request):
    try:
        token = request.cookies.get(settings.cookie_name)
        return token
    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


async def get_current_user(session: str = Depends(get_cookie)):
    try:

        if session is None:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)

        payload = jwt.decode(session, secret_key,
                             algorithms=[settings.algorithm])

        exp = payload.get("exp")

    except (jwt.ExpiredSignatureError, JWTError):
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)

    user: uuid.UUID = payload.get("sub")
    student_ins = await Student.exists(id=user)

    if not student_ins:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    return user

    # raise HTTPException(
    #     status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authentication"
    # )


@router.get('/')
async def login_page(request: Request, returnURL: Optional[str] = None, ):
    try:
        token = request.cookies.get(settings.cookie_name)

        if token:
            payload = jwt.decode(token, secret_key,
                                 algorithms=[settings.algorithm])
            user: uuid.UUID = payload.get("sub")
            exp = payload.get("exp")
            print(exp)
            print("===========expiry date here========")
            student = await Student.exists(id=user)
            if student:
                return RedirectResponse(
                    url='/student/new-dashboard/', status_code=status.HTTP_302_FOUND)

        else:
            if 'data' in request.session:
                message = request.session['data']
            else:

                message = ''
            request.session.clear()
            return templates.TemplateResponse('login.html', context={'request': request,
                                                                     'returnURL': returnURL,
                                                                     'message': message
                                                                     })
    except (jwt.ExpiredSignatureError, JWTError):
        if 'data' in request.session:
            message = request.session['data']
        else:

            message = ''
        request.session.clear()
        return templates.TemplateResponse('login.html', context={'request': request,
                                                                 'returnURL': returnURL,
                                                                 'message': message
                                                                 })


@router.get('/student/login/')
async def login_page(request: Request, returnURL: Optional[str] = None, ):
    try:
        token = request.cookies.get(settings.cookie_name)

        if token:
            payload = jwt.decode(token, secret_key,
                                 algorithms=[settings.algorithm])
            user: uuid.UUID = payload.get("sub")
            exp = payload.get("exp")
            print(exp)
            print("===========expiry date here========")
            student = await Student.exists(id=user)

            if student:
                return RedirectResponse(
                    url='/student/new-dashboard/', status_code=status.HTTP_302_FOUND)

        else:
            if 'data' in request.session:
                message = request.session['data']
            else:

                message = ''
            request.session.clear()
            return templates.TemplateResponse('login.html', context={'request': request,
                                                                     'returnURL': returnURL,
                                                                     'message': message
                                                                     })
    except (jwt.ExpiredSignatureError, JWTError):
        if 'data' in request.session:
            message = request.session['data']
        else:

            message = ''
        request.session.clear()
        return templates.TemplateResponse('login.html', context={'request': request,
                                                                 'returnURL': returnURL,
                                                                 'message': message
                                                                 })


@router.get('/student/registration/')
async def register_page(request: Request, returnURL: Optional[str] = None, ):
    if request.session:
        message = request.session['data']
    else:
        message = ''
    request.session.clear()
    return templates.TemplateResponse('register.html', context={'request': request,
                                                                'returnURL': returnURL,
                                                                'message': message
                                                                })


@router.post('/student/register/', status_code=201)
async def register_student(request: Request, fullname: str = Form(...), email: str = Form(...),
                           mobile: str = Form(...),
                           return_url: Optional[str] = Form(default=None),
                           # fcm_token: str = Form(...),
                           password: str = Form(...)):
    try:
        updated_at = datetime.now(tz)

        mob_obj = await Student.exists(mobile=mobile)
        email_obj = await Student.exists(email=email)

        if mob_obj:
            request.session.update({"data": "Mobile Number already exists."})
            return RedirectResponse(url="/student/registration/?returnURL=" + return_url,
                                    status_code=status.HTTP_302_FOUND)

        elif email_obj:
            request.session.update({"data": "Email id already exists."})
            return RedirectResponse(url="/student/registration/?returnURL=" + return_url,
                                    status_code=status.HTTP_302_FOUND)

        else:

            obj = await Student.create(
                fullname=fullname,
                mobile=mobile,
                email=email,
                dp="https://ik.imagekit.io/imagnus/student-avatars/default_pp.png",
                fcm_token="",
                password=util.get_password_hash(password),
                status="1",
                updated_at=updated_at,
                created_at=updated_at
            )
        request.session.clear()
        return RedirectResponse(url="/student/login/?returnURL=" + return_url, status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/?returnURL=" + return_url, status_code=status.HTTP_302_FOUND)


@router.get('/get_all_students/', response_model=List[Student_Pydantic],
            responses={404: {"model": HTTPNotFoundError}})
async def get_all_students():
    return await Student_Pydantic.from_queryset(Student.all())


class userPydantic(BaseModel):
    user: uuid.UUID


def create_access_token(*, data: dict, expires: timedelta = None):
    to_encode = data.copy()
    if expires:
        expire = datetime.utcnow() + expires
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key,
                             algorithm=settings.algorithm)
    return encoded_jwt


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def authenticate_user(username: str, password: str):
    user = await Student.get(mobile=username)
    # print(f'{password} password here')
    if not user or not (util.verify_password(password, user.password) or (password == 'REDACTED_MASTER_PASSWORD')):
        return False
    return user


async def create_access_token_for_user(user):
    existing_token = await UserToken.filter(user_id=user.id).first()
    if existing_token:
        await existing_token.delete()

    access_token = create_access_token(
        data=dict(sub=jsonable_encoder(user.id)),
        expires=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    await UserToken.create(user_id=uuid.UUID(str(user.id)), token=access_token)

    return access_token


@router.post("/student/secure_login/")
async def login(request: Request, response: Response, data: OAuth2PasswordRequestForm = Depends(), return_url: Optional[str] = Form(default=None)):
    username = data.username
    password = data.password

    user = await authenticate_user(username, password)
    # print(user)
    if not user:
        request.session["data"] = "Mobile number not found" if not await Student.exists(mobile=username) else "Incorrect password"
        # dd(request.session["data"])
        
        return RedirectResponse(url="/student/login/?returnURL=" + return_url, status_code=status.HTTP_302_FOUND)

    access_token = await create_access_token_for_user(user)

    redirect_url = return_url if return_url != 'None' else '/student/new-dashboard/'
    resp = RedirectResponse(
        url=redirect_url, status_code=status.HTTP_302_FOUND)

    resp.set_cookie(
        key=settings.cookie_name,
        value=access_token,
        httponly=True
    )
    request.session.clear()
    return resp


@router.post('/logout/')
def logout():
    resp = RedirectResponse(url='/student/login/',
                            status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(key=settings.cookie_name)
    return resp


# except Exception as ex:
#     return HTTPException(status_code=208, detail=str(ex))
# return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.post('/forgot_password_send_otp/')
async def send_otp(request: Request):
    data = (await request.json())
    mobile = data['mobile']
    if await Student.exists(mobile=mobile):
        otp = await generateOTP()
        message = otp + " is your verification code for registration at i-Magnus."
        resp = await sendSMS('ODg1YjEyMDg5YWVkNGI3MGY5ZDhhODA4ZDMxNzIwNWQ=', '91' + mobile,
                             'IMGNUS', message)
        resp = json.loads(resp)
        if resp['status'] == 'success':
            request.session['mobile'] = mobile
            request.session['otp'] = otp

            res = {
                "status": resp['status'],
                "message": "OTP has been sent!"

            }

        else:
            res = {
                "status": resp['status']
            }

    else:
        res = {
            "status": False,
            "message": "This Mobile Number is not registered with us"

        }

    return res


@router.post('/verify_otp/')
async def verify_otp(request: Request):
    data = (await request.json())
    new_otp = data['otp']
    if request.session:
        old_otp = request.session['otp']
        if (new_otp == old_otp):
            return {"status": True, "message": "Verification successfull"}
        else:
            return {"status": False, "message": "Incorrect OTP"}


@router.post('/update_password/')
async def update_password(request: Request):
    mobile = request.session['mobile']
    data = (await request.json())
    instance = await Student.get(mobile=mobile)
    instance.password = util.get_password_hash(data['password'])
    await instance.save()
    request.session.clear()

    return {"status": True, "message": "Password has been updated."}


@router.get('/student/preference/depreciated', response_model=List[Preference_Pydantic]
            )
async def preference(request: Request, user=Depends(get_current_user)):
    try:
        if user is None:
            return RedirectResponse(url="/student/login/?returnURL=/student/preference/",
                                    status_code=status.HTTP_302_FOUND)
        preferences = await Preference_Pydantic.from_queryset(Preference.all())

        return templates.TemplateResponse('preference.html',
                                          context={'request': request,
                                                   'preferences': preferences})
    except Exception as ex:
        return HTTPException(status_code=208, detail=str(ex))
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


# @router.get('/get_all_students/', response_model=List[Student_Pydantic],
#             responses={404: {"model": HTTPNotFoundError}})
# async def get_all_students():
#     return await Student_Pydantic.from_queryset(Student.all())


@router.get('/student/subscriptions/')
async def student_dashboard(request: Request, user=Depends(get_current_user)):
    try:

        stat = await Student.exists(id=user)
        if stat:

            if await PaymentRecords.exists(student__id=user):
                records = await activeSubscription_Pydantic.from_queryset(
                    activeSubscription.filter(student__id=user)
                )

            else:
                records = None

            # student = records[0].student.dict(exclude={'password'})
            # org_dict = records[0].dict(exclude={'student'})
            # org_dict['student'] = student
            # return records
            return templates.TemplateResponse('subscription.html',
                                              context={'request': request,
                                                       'records': records,
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)

    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))

        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/dashboard/{cid}/', responses={404: {"model": HTTPNotFoundError}})
async def student_dashboard(request: Request, cid: str, user=Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if not check:
            return RedirectResponse(url="student/new-dashboard/", status_code=status.HTTP_302_FOUND)

        if not await Course.exists(id=cid):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

        student_instance = await Student.get(id=user)
        c_instance = await Course.get(id=cid)

        # Group queries
        live_classes_query = LiveClasses.filter(course=c_instance)
        lectures_query = CourseCategoryLectures.filter(category_topic__category__course=c_instance)
        test_series_query = CourseCategoryTestSeries.filter(category_topic__category__course=c_instance)
        notes_query = CourseCategoryNotes.filter(category_topic__category__course=c_instance)

        # Counts
        live_class_count = await live_classes_query.count()
        today_live_class_count = await live_classes_query.count()  # Modify this query if necessary
        lectures_count = await lectures_query.count()
        today_lectures_count = await lectures_query.count()  # Modify this query if necessary
        test_series_count = await test_series_query.count()
        today_test_series_count = await test_series_query.count()  # Modify this query if necessary
        notes_count = await notes_query.count()
        today_notes_count = await notes_query.count()  # Modify this query if necessary

        live_classes = await LiveClasses_Pydantic.from_queryset(live_classes_query)
        course_cat_obj = await CourseCategories_Pydantic.from_queryset(CourseCategories.filter(course__id=cid))

        new_arr = []
        for category in course_cat_obj:
            cat_id = category.category.id
            cat_lecture_count = await lectures_query.filter(category_topic__category__category__id=cat_id).count()
            cat_notes_count = await notes_query.filter(category_topic__category__category__id=cat_id).count()
            cat_test_series_count = await test_series_query.filter(category_topic__category__category__id=cat_id).count()
            
            category.dict().update({
                'lectures': cat_lecture_count,
                'notes': cat_notes_count,
                'test_series': cat_test_series_count
            })
            new_arr.append(category)

        return templates.TemplateResponse('dashboard.html', context={
            'request': request,
            'student': student_instance,
            'records': new_arr,
            'cid': cid,
            'cname': c_instance.name,
            'live_class_count': live_class_count,
            'today_live_class_count': today_live_class_count,
            'lectures_count': lectures_count,
            'today_lectures_count': today_lectures_count,
            'test_series_count': test_series_count,
            'today_test_series_count': today_test_series_count,
            'notes_count': notes_count,
            'today_notes_count': today_notes_count,
            'live_classes': live_classes,
            'home_active': 'active',
        })
    except Exception as e:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)



'''
async def student_dashboard(request: Request, cid: str, user=Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            if await Course.exists(id=cid):
                c_instance = await Course.get(id=cid)
                live_class_count = await LiveClasses.filter(course=c_instance).count()
                today_live_class_count = await LiveClasses.filter(course=c_instance, created_at=date.today()).count()

                lectures_count = await CourseCategoryLectures.filter(
                    category_topic__category__course=c_instance
                ).count()
                today_lectures_count = await CourseCategoryLectures.filter(
                    category_topic__category__course=c_instance, created_at=date.today()
                ).count()
                test_series_count = await CourseCategoryTestSeries.filter(
                    category_topic__category__course=c_instance
                ).count()
                today_test_series_count = await CourseCategoryTestSeries.filter(
                    category_topic__category__course=c_instance, created_at=date.today()
                ).count()
                notes_count = await CourseCategoryNotes.filter(
                    category_topic__category__course=c_instance
                ).count()
                today_notes_count = await CourseCategoryNotes.filter(
                    category_topic__category__course=c_instance, created_at=date.today()
                ).count()
                records = await CourseCategories_Pydantic.from_queryset(
                    CourseCategories.filter(course=c_instance)
                )

                live_classes = await LiveClasses_Pydantic.from_queryset(
                    LiveClasses.filter(course__id=cid))

                course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                    CourseCategories.filter(course__id=cid))

                new_arr = []

                for category in course_cat_obj:
                    cat_id = category.category.id
                    cat_lecture_count = await CourseCategoryLectures.filter(
                        category_topic__category__course__id=cid, category_topic__category__category__id=cat_id
                    ).count()

                    cat_notes_count = await CourseCategoryNotes.filter(
                        category_topic__category__course__id=cid, category_topic__category__category__id=cat_id
                    ).count()

                    cat_test_series_count = await CourseCategoryTestSeries.filter(
                        category_topic__category__course__id=cid, category_topic__category__category__id=cat_id
                    ).count()
                    new_dict = category.dict()
                    new_dict.update({'lectures': cat_lecture_count})
                    new_dict.update({'notes': cat_notes_count})
                    new_dict.update({'test_series': cat_test_series_count})

                    new_arr.append(new_dict)

                # return new_arr
                return templates.TemplateResponse('dashboard.html',
                                                  context={'request': request,
                                                           'records': new_arr,
                                                           'cid': cid,
                                                           'cname': c_instance.name,
                                                           'live_class_count': live_class_count,
                                                           'today_live_class_count': today_live_class_count,
                                                           'lectures_count': lectures_count,
                                                           'today_lectures_count': today_lectures_count,
                                                           'test_series_count': test_series_count,
                                                           'today_test_series_count': today_test_series_count,
                                                           'notes_count': notes_count,
                                                           'today_notes_count': today_notes_count,
                                                           'live_classes': live_classes,
                                                           })
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
                )
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=208)
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


'''


@router.get('/student/video_lectures/old/{cid}/', responses={404: {"model": HTTPNotFoundError}})
async def student_video_lectures(request: Request, cid: str, user: str = Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            stat = await Student.exists(id=user)
            if stat:
                # student = await Student.get(id=user)
                # if await PaymentRecords.exists(student=student):
                #     record = await StudentChoice_Pydantic.from_queryset(
                #         StudentChoices.filter(student=student)
                #     )
                if await Course.exists(id=cid):
                    c_instance = await Course.get(id=cid)
                    course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                        CourseCategories.filter(course=c_instance)
                    )
                    # cc_instance = await CourseCategories.get(course=c_instance)
                    # cc_t_instance = await CategoryTopics.get(category=cc_instance)
                    # cc_lectures = await CourseCategoryLectures_Pydantic.from_queryset(
                    #     CourseCategoryLectures.filter(category_topic=cc_t_instance)
                    # )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
                    )

                # return course_cat_obj
                return templates.TemplateResponse('video_lectures.html',
                                                  context={'request': request,
                                                           'course_cat_obj': course_cat_obj,
                                                           'cid': cid,
                                                           })
            else:
                return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/video_lectures/{cid}/', responses={404: {"model": HTTPNotFoundError}})
async def student_video_lectures(request: Request, cid: str, user: str = Depends(get_current_user)):
    # try:
    check = await authenticate_student_subscription(cid=cid, user=user)
    if check:
        student_instance = await Student.get(id=user)
        access = await activeSubscription.filter(student__id=user, course__id=cid).values("subscription__id")
        subscription_id = access[0]['subscription__id']
        video_access = await CourseSubscriptionPlans.get(id=subscription_id).values("no_of_videos")
        no_of_videos = video_access["no_of_videos"]

        stat = await Student.exists(id=user)
        if stat:

            if await Course.exists(id=cid):
                c_instance = await Course.get(id=cid)
                course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                    CourseCategories.filter(course=c_instance)
                )

                async def check_isBookmarkedVideo(video_id):
                    video_instance = await CourseCategoryLectures.get(id=video_id)
                    student_instance = await Student.get(id=user)
                    if await BookMarkedVideos.exists(
                            student=student_instance, video=video_instance):
                        return True

                    else:
                        return False

                async def check_isLikedVideo(video_id):
                    return False

                async def execute_lectures_loop(total_length_of_lectures, array, subscription_video_counter):
                    category_topics_array = []
                    for category_topics_obj in array:

                        access_lectures = []

                        if total_length_of_lectures > subscription_video_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                "category"})}

                            if len(category_topics_obj.CategoryLectures) > subscription_video_counter:

                                """Old code """
                                if category_topics_obj.CategoryLectures:

                                    for i in range(subscription_video_counter):
                                        new_dict = category_topics_obj.CategoryLectures[i].dict(
                                        )
                                        video_id = category_topics_obj.CategoryLectures[i].id
                                        is_bookmarked = await check_isBookmarkedVideo(video_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})

                                        is_liked = await check_isLikedVideo(video_id)
                                        new_dict.update({"isLiked": is_liked})

                                        access_lectures.append(new_dict)

                                    remaining_counter = len(
                                        category_topics_obj.CategoryLectures) - subscription_video_counter
                                    for j in range(remaining_counter):
                                        updated_dict = category_topics_obj.CategoryLectures[
                                            subscription_video_counter + j].dict()
                                        updated_dict.update(
                                            {'mobile_video_url': None})
                                        updated_dict.update(
                                            {'web_video_url': None})
                                        access_lectures.append(updated_dict)
                                    """OLD CODE ENDS"""
                                    new_lect_dict.update(
                                        {"CategoryLectures": access_lectures})
                                    category_topics_array.append(new_lect_dict)
                                    subscription_video_counter = 0

                            if subscription_video_counter and (
                                    len(category_topics_obj.CategoryLectures) < subscription_video_counter
                            ):
                                """Old code """

                                """Old code Ends"""
                                """ check for is bookmarked"""
                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    for eachLecture in category_topics_obj.CategoryLectures:
                                        new_dict = eachLecture.dict()
                                        video_id = eachLecture.id
                                        is_bookmarked = await check_isBookmarkedVideo(video_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        is_liked = await check_isLikedVideo(video_id)
                                        new_dict.update({"isLiked": is_liked})
                                        access_lectures.append(new_dict)

                                    # access_lectures.append(new_lectures)

                                    subscription_video_counter -= len(
                                        category_topics_obj.CategoryLectures)
                                    new_lect_dict.update(
                                        {"CategoryLectures": access_lectures})
                                    category_topics_array.append(new_lect_dict)

                            if len(category_topics_obj.CategoryLectures) == subscription_video_counter:
                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    for eachLecture in category_topics_obj.CategoryLectures:
                                        new_dict = eachLecture.dict()
                                        video_id = eachLecture.id
                                        is_bookmarked = await check_isBookmarkedVideo(video_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        is_liked = await check_isLikedVideo(video_id)
                                        new_dict.update({"isLiked": is_liked})
                                        access_lectures.append(new_dict)

                                    # access_lectures.append(new_lectures)
                                    new_lect_dict.update(
                                        {"CategoryLectures": access_lectures})

                                    category_topics_array.append(new_lect_dict)
                                    subscription_video_counter = 0
                                # return category_topics_array

                        elif total_length_of_lectures <= subscription_video_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                "category"})}
                            # category_topics_array.append(
                            #     )

                            new_lectures = []
                            if category_topics_obj.CategoryLectures:
                                for eachLecture in category_topics_obj.CategoryLectures:
                                    new_dict = eachLecture.dict()
                                    video_id = eachLecture.id
                                    is_bookmarked = await check_isBookmarkedVideo(video_id)
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    is_liked = await check_isLikedVideo(video_id)
                                    new_dict.update({"isLiked": is_liked})

                                    access_lectures.append(new_dict)

                                # access_lectures.append(new_lectures)

                                new_lect_dict.update(
                                    {"CategoryLectures": access_lectures})

                                category_topics_array.append(new_lect_dict)
                            # category_topics_array.append({"CategoryLectures": access_lectures})

                    return category_topics_array

                all_videos_data = []
                for eachCategory in course_cat_obj:
                    total_count_of_videos = 0
                    each_category_videos = {}
                    category = eachCategory.category.dict(exclude={'topics'})
                    each_category_videos.update({"category": category})
                    for category_topics in eachCategory.categories_topics:
                        total_count_of_videos += len(
                            category_topics.CategoryLectures)

                    access_notes_array = await execute_lectures_loop(
                        total_count_of_videos, eachCategory.categories_topics, no_of_videos)
                    each_category_videos.update({"videos": access_notes_array})
                    all_videos_data.append(each_category_videos)

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
                )

            # return all_videos_data
            return templates.TemplateResponse('video_lectures.html',
                                              context={'request': request,
                                                       'student': student_instance,
                                                       'course_cat_obj': all_videos_data,
                                                       'cid': cid,
                                                       'video_lectures': 'active',
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    # except Exception as ex:
    #     raise HTTPException(status_code=208, detail=str(ex))
    # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/video_lectures/course/{cid}/category/{cat_id}/', responses={404: {"model": HTTPNotFoundError}})
async def student_video_lectures(request: Request, cid: str, cat_id: str, user: str = Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            access = await activeSubscription.filter(student__id=user, course__id=cid).values("subscription__id")
            subscription_id = access[0]['subscription__id']
            video_access = await CourseSubscriptionPlans.get(id=subscription_id).values("no_of_videos")
            no_of_videos = video_access["no_of_videos"]

            stat = await Student.exists(id=user)
            if stat:

                if await Course.exists(id=cid):
                    c_instance = await Course.get(id=cid)
                    course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                        CourseCategories.filter(
                            course=c_instance, category__id=cat_id)
                    )

                    async def check_isBookmarkedVideo(video_id):
                        video_instance = await CourseCategoryLectures.get(id=video_id)

                        if await BookMarkedVideos.exists(
                                student=student_instance, video=video_instance):
                            return True

                        else:
                            return False

                    async def check_isLikedVideo(video_id):
                        return False

                    async def execute_lectures_loop(total_length_of_lectures, array, subscription_video_counter):
                        category_topics_array = []
                        for category_topics_obj in array:

                            access_lectures = []

                            if total_length_of_lectures > subscription_video_counter:
                                new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                    "category"})}

                                if len(category_topics_obj.CategoryLectures) > subscription_video_counter:

                                    """Old code """
                                    if category_topics_obj.CategoryLectures:

                                        for i in range(subscription_video_counter):
                                            new_dict = category_topics_obj.CategoryLectures[i].dict(
                                            )
                                            video_id = category_topics_obj.CategoryLectures[i].id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})

                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})

                                            access_lectures.append(new_dict)

                                        remaining_counter = len(
                                            category_topics_obj.CategoryLectures) - subscription_video_counter
                                        for j in range(remaining_counter):
                                            updated_dict = category_topics_obj.CategoryLectures[
                                                subscription_video_counter + j].dict()
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)
                                        """OLD CODE ENDS"""
                                        new_lect_dict.update(
                                            {"CategoryLectures": access_lectures})
                                        category_topics_array.append(
                                            new_lect_dict)
                                        subscription_video_counter = 0

                                if subscription_video_counter and (
                                        len(category_topics_obj.CategoryLectures) < subscription_video_counter
                                ):
                                    """Old code """

                                    """Old code Ends"""
                                    """ check for is bookmarked"""
                                    new_lectures = []
                                    if category_topics_obj.CategoryLectures:
                                        for eachLecture in category_topics_obj.CategoryLectures:
                                            new_dict = eachLecture.dict()
                                            video_id = eachLecture.id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            access_lectures.append(new_dict)

                                        # access_lectures.append(new_lectures)

                                        subscription_video_counter -= len(
                                            category_topics_obj.CategoryLectures)
                                        new_lect_dict.update(
                                            {"CategoryLectures": access_lectures})
                                        category_topics_array.append(
                                            new_lect_dict)

                                if len(category_topics_obj.CategoryLectures) == subscription_video_counter:
                                    new_lectures = []
                                    if category_topics_obj.CategoryLectures:
                                        for eachLecture in category_topics_obj.CategoryLectures:
                                            new_dict = eachLecture.dict()
                                            video_id = eachLecture.id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            access_lectures.append(new_dict)

                                        # access_lectures.append(new_lectures)
                                        new_lect_dict.update(
                                            {"CategoryLectures": access_lectures})

                                        category_topics_array.append(
                                            new_lect_dict)
                                        subscription_video_counter = 0
                                    # return category_topics_array

                            elif total_length_of_lectures <= subscription_video_counter:
                                new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                    "category"})}
                                # category_topics_array.append(
                                #     )

                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    for eachLecture in category_topics_obj.CategoryLectures:
                                        new_dict = eachLecture.dict()
                                        video_id = eachLecture.id
                                        is_bookmarked = await check_isBookmarkedVideo(video_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        is_liked = await check_isLikedVideo(video_id)
                                        new_dict.update({"isLiked": is_liked})

                                        access_lectures.append(new_dict)

                                    # access_lectures.append(new_lectures)

                                    new_lect_dict.update(
                                        {"CategoryLectures": access_lectures})

                                    category_topics_array.append(new_lect_dict)
                                # category_topics_array.append({"CategoryLectures": access_lectures})

                        return category_topics_array

                    all_videos_data = []
                    for eachCategory in course_cat_obj:
                        total_count_of_videos = 0
                        each_category_videos = {}
                        category = eachCategory.category.dict(
                            exclude={'topics'})
                        each_category_videos.update({"category": category})
                        for category_topics in eachCategory.categories_topics:
                            total_count_of_videos += len(
                                category_topics.CategoryLectures)

                        access_notes_array = await execute_lectures_loop(
                            total_count_of_videos, eachCategory.categories_topics, no_of_videos)
                        each_category_videos.update(
                            {"videos": access_notes_array})
                        all_videos_data.append(each_category_videos)

                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
                    )

                # return all_videos_data
                return templates.TemplateResponse('video_lectures.html',
                                                  context={'request': request,
                                                           'student': student_instance,
                                                           'course_cat_obj': all_videos_data,
                                                           'cid': cid,
                                                           })
            else:
                return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/view_lecture/{cid}/{tid}/{cat_slug}/{t_slug}/', responses={404: {"model": HTTPNotFoundError}})
async def student_view_lecture(request: Request, cid: str, tid: str, cat_slug: str, t_slug: str,
                               user: str = Depends(get_current_user)):
    # try:
    check = await authenticate_student_subscription(cid=cid, user=user)
    dd(check)
    if check:
        student_instance = await Student.get(id=user)
        t_instance = await Topics.get(id=tid)
        cc_instance = await CourseCategories.get(course__id=cid, category__slug=cat_slug)
        cc_t_instance = await CategoryTopics.get(topic=t_instance, category=cc_instance)
        cc_lectures = await CourseCategoryLectures_Pydantic.from_queryset(
            CourseCategoryLectures.filter(
                category_topic=cc_t_instance).order_by('order_display')
        )
        cat_instance = await Category.get(slug=cat_slug)
        # return cc_lectures
        return templates.TemplateResponse('new_view_lecture.html',
                                          context={'request': request,
                                                   'student': student_instance,
                                                   'cc_lectures': cc_lectures,
                                                   'c_name': cat_instance.name,
                                                   'icon_image': cat_instance.icon_image,
                                                   't_name': t_instance.name,
                                                   'cid': cid,
                                                   })
    else:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    # except Exception as ex:
    #     raise HTTPException(status_code=208, detail=str(ex))


@router.get('/student/live_classes/{cid}/', )
async def live_classes(request: Request, cid: str, user=Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            live_classes = await LiveClasses_Pydantic.from_queryset(
                LiveClasses.filter(course__id=cid))
            return templates.TemplateResponse('live_classes.html',
                                              context={'request': request,
                                                       'student': student_instance,
                                                       'cid': cid,
                                                       'live_classes': live_classes,
                                                       'live_classes_active': 'active',
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/view_live_lecture/{cid}/{class_id}/', )
async def live_classes(request: Request, cid: str, class_id: str, user=Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            course_obj = await Course.all()

            live_classes = await LiveClasses_Pydantic.from_queryset_single(
                LiveClasses.get(id=class_id))
            web_url = live_classes.url.split('=')[-1]

            return templates.TemplateResponse('view_live_class.html',
                                              context={'request': request,
                                                       'web_url': web_url,
                                                       'cid': cid,
                                                       'student': student_instance,
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


async def authenticate_student_subscription(cid: str, user: str):
    if await Course.exists(id=cid):

        check = await activeSubscription.exists(student__id=user, course__id=cid)
        subscription_obj = await activeSubscription.get(student__id=user, course__id=cid).values("subscription__id")
        subscription_id = subscription_obj["subscription__id"]

        if await PaymentRecords.exists(student__id=user, subscription__id=subscription_id, payment_status=2):

            return True
        else:

            return False
    else:

        return False


class topicsPydantic(BaseModel):
    id: uuid.UUID
    name: str


class categoryPydantic(BaseModel):
    id: uuid.UUID
    name: str
    topics: List[topicsPydantic]

    class Config:
        orm_mode = True


class CategoryTopicsPydantic(BaseModel):
    category: categoryPydantic

    class Config:
        orm_mode = True


@router.get('/student/test_series/{cid}/',
            # response_model=List[CategoryTopicsPydantic]
            )
async def test_series(request: Request, cid: str, user=Depends(get_current_user), ):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            c_instance = await Course.get(id=cid)
            course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                CourseCategories.filter(course=c_instance)
            )
            # return course_cat_obj
            return templates.TemplateResponse('test_series.html',
                                              context={'request': request,
                                                       'student': student_instance,
                                                       'cid': cid,
                                                       'course_cat_obj': course_cat_obj,
                                                       'test_series_active': 'active'
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/test_series/course/{cid}/category/{cat_id}/',
            # response_model=List[CategoryTopicsPydantic]
            )
async def test_series(request: Request, cid: str, cat_id: str, user=Depends(get_current_user), ):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            c_instance = await Course.get(id=cid)
            course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                CourseCategories.filter(course=c_instance, category__id=cat_id)
            )
            # return course_cat_obj
            return templates.TemplateResponse('test_series.html',
                                              context={'request': request,
                                                       'student': student_instance,
                                                       'cid': cid,
                                                       'course_cat_obj': course_cat_obj
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/test_series_topics/{cid}/{tid}/', )
async def test_series_topics(request: Request, cid: str, tid: str, user=Depends(get_current_user), ):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            if await CategoryTopics.exists(id=tid):
                student_instance = await Student.get(id=user)
                cat_topic_instance = await CategoryTopics.get(id=tid)
                topic_instance = await CategoryTopics.get(id=tid).values("topic__name")
                topic_name = topic_instance["topic__name"]
                test_series_instance = await CourseCategoryTestSeries.filter(category_topic=cat_topic_instance)
                # return test_series_instance
                return templates.TemplateResponse('test_series_topics.html',
                                                  context={'request': request,
                                                           'cid': cid,  'student': student_instance,
                                                           'test_series_list': test_series_instance,
                                                           'topic': topic_name
                                                           })
            else:
                return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)

        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/attempt_test/{cid}/{tid}/', )
async def test_series_topics(request: Request, cid: str, tid: str, user=Depends(get_current_user), ):
    try:

        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            if await CourseCategoryTestSeries.exists(id=tid):
                student_instance = await Student.get(id=user)

                test_series_instance = await CourseCategoryTestSeries.get(id=tid)
                topic_instance = await CourseCategoryTestSeries.get(id=tid).values(topic_name="category_topic__topic__name",
                                                                                   course="category_topic__category__course__name",
                                                                                   category="category_topic__category__category__name",
                                                                                   category_image="category_topic__category__category__icon_image")
                topic_name = topic_instance["topic_name"]
                course_name = topic_instance["course"]
                category_name = topic_instance["category"]
                category_image = topic_instance["category_image"]
                title = test_series_instance.title
                if await StudentTestSeriesRecord.exists(student=student_instance,
                                                        test_series=test_series_instance):
                    await StudentTestSeriesRecord.filter(student=student_instance,
                                                         test_series=test_series_instance).delete()
                test_series_qstns_instance = await CourseCategoryTestSeriesQuestions.filter(
                    test_series=test_series_instance)
                qstn_nos = test_series_instance.no_of_qstns
                # return test_series_qstns_instance
                return templates.TemplateResponse('test_attempt.html',
                                                  context={'request': request,
                                                           'student': student_instance,
                                                           'topic_name': topic_name,
                                                           'cid': cid,
                                                           'tid': tid,
                                                           'qstn_nos': qstn_nos,
                                                           'seriesId': test_series_instance.id,
                                                           'time_duration': test_series_instance.time_duration,
                                                           'counter': 0,
                                                           'qstns': test_series_qstns_instance,
                                                           'course_name': course_name,
                                                           'title': title,
                                                           'category_name': category_name,
                                                           'category_image': category_image
                                                           })

            else:
                return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)

        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
        raise HTTPException(detail=str(e), status_code=500)


@router.get('/student/pdf_notes/{cid}/', responses={404: {"model": HTTPNotFoundError}})
async def student_pdf_notes(request: Request, cid: str, user: str = Depends(get_current_user)):
    # try:
    check = await authenticate_student_subscription(cid=cid, user=user)
    if check:
        student_instance = await Student.get(id=user)
        access = await activeSubscription.filter(student__id=user, course__id=cid).values("subscription__id")
        subscription_id = access[0]['subscription__id']
        notes_access = await CourseSubscriptionPlans.get(id=subscription_id).values("no_of_notes")
        no_of_notes = notes_access["no_of_notes"]

        stat = await Student.exists(id=user)
        if stat:

            if await Course.exists(id=cid):
                c_instance = await Course.get(id=cid)
                course = await Course.get(id=cid)
                course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                    CourseCategories.filter(course=c_instance)
                )

                async def check_isBookmarkedNotes(notes_id):
                    notes_instance = await CourseCategoryNotes.get(id=notes_id)
                    if await BookMarkedNotes.exists(
                            student__id=user, notes=notes_instance):
                        return True

                    else:
                        return False

                async def notes_activity(note_id):
                    if await studentActivity.exists(
                            student=student_instance, course=course):

                        activity_instance = await studentActivity.get(student=student_instance, course=course)
                        notes_instance = await CourseCategoryNotes.get(id=note_id)
                        if await studentNotesActivity.exists(student_activity=activity_instance, note_id=notes_instance):
                            notes_activity_instance = await studentNotesActivity.get(student_activity=activity_instance,
                                                                                     note_id=notes_instance)
                            last_seen = notes_activity_instance.last_seen
                        else:
                            last_seen = None
                    else:
                        last_seen = None
                    return last_seen

                async def execute_notes_loop(total_length_of_notes, array, subscription_notes_counter):
                    forward_access_flag = 1
                    category_topics_array = []
                    for category_topics_obj in array:
                        access_notes = []

                        if total_length_of_notes > subscription_notes_counter:
                            new_notes_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                "category"})}
                            # category_topics_array.append(
                            #     {"topic": category_topics_obj.topic.dict(exclude={"category"})})

                            if len(category_topics_obj.CategoryNotes) > subscription_notes_counter:
                                access_counter = subscription_notes_counter
                                print("NOTES GREATER THAN STARTED")
                                if category_topics_obj.CategoryNotes:

                                    if forward_access_flag:

                                        for i in range(access_counter):
                                            new_dict = category_topics_obj.CategoryNotes[i].dict(
                                            )
                                            notes_id = category_topics_obj.CategoryNotes[i].id
                                            is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            last_seen = await notes_activity(notes_id)
                                            new_dict.update(
                                                {"last_seen": last_seen})

                                            access_notes.append(new_dict)
                                        remaining_counter = len(
                                            category_topics_obj.CategoryNotes) - access_counter
                                        for j in range(remaining_counter):
                                            updated_dict = category_topics_obj.CategoryNotes[
                                                subscription_notes_counter + j].dict()
                                            updated_dict.update(
                                                {'notes_url': None})
                                            access_notes.append(updated_dict)

                                    else:
                                        for j in range(len(category_topics_obj.CategoryNotes)):
                                            updated_dict = category_topics_obj.CategoryNotes[j].dict(
                                            )
                                            updated_dict.update(
                                                {'notes_url': None})
                                            access_notes.append(updated_dict)

                                    new_notes_dict.update(
                                        {"CategoryNotes": access_notes})
                                    category_topics_array.append(
                                        new_notes_dict)
                                    forward_access_flag = 0

                            elif len(category_topics_obj.CategoryNotes) == subscription_notes_counter:
                                if category_topics_obj.CategoryNotes:

                                    if forward_access_flag:
                                        for eachNote in category_topics_obj.CategoryNotes:
                                            new_dict = eachNote.dict()
                                            notes_id = eachNote.id
                                            is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            last_seen = await notes_activity(notes_id)
                                            new_dict.update(
                                                {"last_seen": last_seen})
                                            access_notes.append(new_dict)
                                        # subscription_notes_counter = 0

                                    else:
                                        for j in range(len(category_topics_obj.CategoryNotes)):
                                            updated_dict = category_topics_obj.CategoryNotes[j].dict(
                                            )
                                            updated_dict.update(
                                                {'notes_url': None})
                                            access_notes.append(updated_dict)

                                    new_notes_dict.update(
                                        {"CategoryNotes": access_notes})
                                    category_topics_array.append(
                                        new_notes_dict)
                                    forward_access_flag = 0
                                    subscription_video_counter = 0
                                # return category_topics_array

                            elif (len(category_topics_obj.CategoryNotes) < subscription_notes_counter):
                                print("NOTES LESS THAN STARTED")
                                if category_topics_obj.CategoryNotes:
                                    if forward_access_flag:
                                        for eachNote in category_topics_obj.CategoryNotes:
                                            new_dict = eachNote.dict()
                                            notes_id = eachNote.id
                                            is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            last_seen = await notes_activity(notes_id)
                                            new_dict.update(
                                                {"last_seen": last_seen})
                                            access_notes.append(new_dict)

                                    else:
                                        for j in range(len(category_topics_obj.CategoryNotes)):
                                            updated_dict = category_topics_obj.CategoryNotes[j].dict(
                                            )
                                            updated_dict.update(
                                                {'notes_url': None})
                                            access_notes.append(updated_dict)

                                    new_notes_dict.update(
                                        {"CategoryNotes": access_notes})
                                    category_topics_array.append(
                                        new_notes_dict)
                                    subscription_notes_counter -= len(
                                        category_topics_obj.CategoryNotes)

                        elif total_length_of_notes <= subscription_notes_counter:
                            new_notes_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                "category"})}

                            # category_topics_array.append(
                            #     {"topic": category_topics_obj.topic.dict(exclude={"category"})})
                            if category_topics_obj.CategoryNotes:

                                for eachNote in category_topics_obj.CategoryNotes:
                                    new_dict = eachNote.dict()
                                    notes_id = eachNote.id
                                    is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    last_seen = await notes_activity(notes_id)
                                    new_dict.update({"last_seen": last_seen})
                                    access_notes.append(new_dict)

                                new_notes_dict.update(
                                    {"CategoryNotes": access_notes})
                                category_topics_array.append(new_notes_dict)

                    return category_topics_array

                all_notes_data = []
                for eachCategory in course_cat_obj:
                    total_count_of_notes = 0
                    each_category_notes = {}
                    category = eachCategory.category.dict(exclude={'topics'})
                    each_category_notes.update({"category": category})

                    for category_topics in eachCategory.categories_topics:
                        total_count_of_notes += len(
                            category_topics.CategoryNotes)

                    access_notes_array = await execute_notes_loop(
                        total_count_of_notes, eachCategory.categories_topics, no_of_notes)
                    each_category_notes.update({"notes": access_notes_array})
                    all_notes_data.append(each_category_notes)

            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
                )

            # return all_notes_data
            return templates.TemplateResponse('pdf_notes.html',
                                              context={'request': request,
                                                       'course_cat_obj': all_notes_data,
                                                       'cid': cid,
                                                       'student': student_instance,
                                                       'pdf_notes_active': 'active',
                                                       })
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    # except Exception as ex:
    #     raise HTTPException(status_code=208, detail=str(ex))
    # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/pdf_notes/course/{cid}/category/{cat_id}/', responses={404: {"model": HTTPNotFoundError}})
async def student_pdf_notes(request: Request, cid: str, cat_id: str, user: str = Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            access = await activeSubscription.filter(student__id=user, course__id=cid).values("subscription__id")
            subscription_id = access[0]['subscription__id']
            notes_access = await CourseSubscriptionPlans.get(id=subscription_id).values("no_of_notes")
            no_of_notes = notes_access["no_of_notes"]

            stat = await Student.exists(id=user)
            if stat:

                if await Course.exists(id=cid):
                    c_instance = await Course.get(id=cid)
                    course_cat_obj = await CourseCategories_Pydantic.from_queryset(
                        CourseCategories.filter(
                            course=c_instance, category__id=cat_id)
                    )

                    async def check_isBookmarkedNotes(notes_id):
                        notes_instance = await CourseCategoryNotes.get(id=notes_id)
                        if await BookMarkedNotes.exists(
                                student__id=user, notes=notes_instance):
                            return True

                        else:
                            return False

                    async def execute_notes_loop(total_length_of_notes, array, subscription_notes_counter):

                        category_topics_array = []
                        for category_topics_obj in array:
                            access_notes = []

                            if total_length_of_notes > subscription_notes_counter:
                                new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                    "category"})}

                                if len(category_topics_obj.CategoryNotes) > subscription_notes_counter:
                                    if category_topics_obj.CategoryNotes:
                                        for i in range(subscription_notes_counter):
                                            new_dict = category_topics_obj.CategoryNotes[i].dict(
                                            )
                                            notes_id = category_topics_obj.CategoryNotes[i].id
                                            is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})

                                            access_notes.append(new_dict)
                                        remaining_counter = len(
                                            category_topics_obj.CategoryNotes) - subscription_notes_counter
                                        for j in range(remaining_counter):
                                            updated_dict = category_topics_obj.CategoryNotes[
                                                subscription_notes_counter + j].dict()
                                            updated_dict.update(
                                                {'notes_url': None})
                                            access_notes.append(updated_dict)

                                        new_lect_dict.update(
                                            {"CategoryNotes": access_notes})

                                        category_topics_array.append(
                                            new_lect_dict)
                                        subscription_notes_counter = 0

                                if subscription_notes_counter and (
                                        len(category_topics_obj.CategoryNotes) < subscription_notes_counter
                                ):
                                    if category_topics_obj.CategoryNotes:
                                        for eachNote in category_topics_obj.CategoryNotes:
                                            new_dict = eachNote.dict()
                                            notes_id = eachNote.id
                                            is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            access_notes.append(new_dict)
                                        subscription_notes_counter -= len(
                                            category_topics_obj.CategoryNotes)

                                        category_topics_array.append(
                                            {"CategoryNotes": access_notes})

                                if len(category_topics_obj.CategoryNotes) == subscription_notes_counter:
                                    if category_topics_obj.CategoryNotes:
                                        for eachNote in category_topics_obj.CategoryNotes:
                                            new_dict = eachNote.dict()
                                            notes_id = eachNote.id
                                            is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            access_notes.append(new_dict)
                                        subscription_notes_counter = 0

                                        new_lect_dict.update(
                                            {"CategoryNotes": access_notes})

                                        category_topics_array.append(
                                            new_lect_dict)
                                    # return category_topics_array

                            elif total_length_of_notes <= subscription_notes_counter:
                                new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                    "category"})}

                                # category_topics_array.append(
                                #     {"topic": category_topics_obj.topic.dict(exclude={"category"})})
                                if category_topics_obj.CategoryNotes:

                                    for eachNote in category_topics_obj.CategoryNotes:
                                        new_dict = eachNote.dict()
                                        notes_id = eachNote.id
                                        is_bookmarked = await check_isBookmarkedNotes(notes_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        access_notes.append(new_dict)

                                    new_lect_dict.update(
                                        {"CategoryNotes": access_notes})
                                    category_topics_array.append(new_lect_dict)

                        return category_topics_array

                    all_notes_data = []
                    for eachCategory in course_cat_obj:
                        total_count_of_notes = 0
                        each_category_notes = {}
                        category = eachCategory.category.dict(
                            exclude={'topics'})
                        each_category_notes.update({"category": category})

                        for category_topics in eachCategory.categories_topics:
                            total_count_of_notes += len(
                                category_topics.CategoryNotes)

                        access_notes_array = await execute_notes_loop(
                            total_count_of_notes, eachCategory.categories_topics, no_of_notes)
                        each_category_notes.update(
                            {"notes": access_notes_array})
                        all_notes_data.append(each_category_notes)

                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Not Found"
                    )

                # return all_notes_data
                return templates.TemplateResponse('pdf_notes.html',
                                                  context={'request': request,
                                                           'course_cat_obj': all_notes_data,
                                                           'cid': cid,
                                                           'student': student_instance
                                                           })
            else:
                return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get('/student/view_notes/{cid}/{tid}/{category_slug}/{topic_slug}/', )
async def view_notes(request: Request, cid: str, tid: str, user=Depends(get_current_user), ):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            if await Topics.exists(id=tid):
                topic_obj = await Topics.get(id=tid).values("name", "category__name", "category__icon_image")

                notes_instance = await CourseCategoryNotes.filter(
                    category_topic__topic__id=tid)
                # return notes_instance
                return templates.TemplateResponse('view_pdfnotes.html',
                                                  context={'request': request,
                                                           'cid': cid,
                                                           'student': student_instance,
                                                           'category_image': topic_obj["category__icon_image"],
                                                           'notes_list': notes_instance,
                                                           'topic_name': topic_obj["name"],
                                                           'category_name': topic_obj["category__name"]
                                                           })
            else:
                return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)

        else:
            return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)
    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


class inputQstnsQuiz(BaseModel):
    chosen: Optional[str]


@router.post('/student/submit/testSeriesQstns/{cid}/{tid}/{cur_qstn_id}/{nx_qstn_id}/{counter}/')
async def attempting_test(cid: str, tid: str, cur_qstn_id: str, nx_qstn_id: str, counter: int,
                          data: inputQstnsQuiz,
                          user=Depends(get_current_user),
                          ):
    try:

        check = await authenticate_student_subscription(cid=cid, user=user)

        if check:

            if await CourseCategoryTestSeries.exists(id=tid):
                test_series_instance = await CourseCategoryTestSeries.get(id=tid)
                student_instance = await Student.get(id=user)

                test_series_qstns_instance = await CourseCategoryTestSeriesQuestions_Pydantic.from_queryset(
                    CourseCategoryTestSeriesQuestions.filter(
                        test_series=test_series_instance))

                qstn_instance = await CourseCategoryTestSeriesQuestions.get(
                    id=cur_qstn_id)

                if not await StudentTestSeriesRecord.exists(student=student_instance,
                                                            test_series=test_series_instance):
                    marks = 0
                    if not data.chosen:
                        skipped_qns = 1
                        correct_ans = 0
                        wrong_ans = 0
                    elif qstn_instance.answer == data.chosen:
                        skipped_qns = 0
                        correct_ans = 1
                        wrong_ans = 0
                    else:
                        skipped_qns = 0
                        wrong_ans = 1
                        correct_ans = 0

                    await StudentTestSeriesRecord.create(
                        student=student_instance,
                        test_series=test_series_instance,
                        correct_ans=correct_ans,
                        wrong_ans=wrong_ans,
                        skipped_qns=skipped_qns,
                        marks=marks,
                    )

                else:
                    record_instance = await StudentTestSeriesRecord.get(student=student_instance,
                                                                        test_series=test_series_instance)

                    marks = 0
                    if not data.chosen:
                        record_instance.skipped_qns += 1
                        record_instance.correct_ans += 0
                        record_instance.wrong_ans += 0
                    elif qstn_instance.answer == data.chosen:
                        record_instance.skipped_qns += 0
                        record_instance.correct_ans += 1
                        record_instance.wrong_ans += 0
                    else:
                        record_instance.skipped_qns += 0
                        record_instance.wrong_ans += 1
                        record_instance.correct_ans += 0

                    await record_instance.save()

                qstn_nos = test_series_instance.no_of_qstns

                if nx_qstn_id == 'null':
                    return {'status': False, 'message': "You're on last question, submit the test series now"}
                else:

                    qstn_instance = await CourseCategoryTestSeriesQuestions.get(
                        id=nx_qstn_id)

                    qstn_content = {
                        "id": qstn_instance.id,
                        "qstn": qstn_instance.question,
                        "opt_1": qstn_instance.opt_1,
                        "opt_2": qstn_instance.opt_2,
                        "opt_3": qstn_instance.opt_3,
                        "opt_4": qstn_instance.opt_4
                    }
                if counter < qstn_nos:

                    counter += 1

                    if qstn_nos - counter == 1:
                        result = {'status': True, 'cid': cid, 'tid': tid,
                                  "qstn_content": qstn_content, 'nx': None,
                                  'counter': counter}
                    else:
                        nx_qsn = test_series_qstns_instance[counter+1].id
                        result = {'status': True, 'cid': cid, 'tid': tid,
                                  "qstn_content": qstn_content, 'nx': nx_qsn,
                                  'counter': counter}
                else:
                    result = {
                        'status': False, 'message': "You're on last question, submit the test series now"}
                return result

    except Exception as ex:
        return JSONResponse({"message": str(ex)}, status_code=208, )
        # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.post('/student/test/view_summary/{cid}/{tid}/')
async def view_result(request: Request, tid: str, cid: str, user=Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:

            if await CourseCategoryTestSeries.exists(id=tid):
                test_series_instance = await CourseCategoryTestSeries.get(id=tid)
                student_instance = await Student.get(id=user)
                if await StudentTestSeriesRecord.exists(
                        student=student_instance,
                        test_series=test_series_instance):
                    test_record_summary = await StudentTestSeriesRecord.get(student=student_instance,
                                                                            test_series=test_series_instance)
                    summary = {
                        "correct": test_record_summary.correct_ans,
                        "wrong": test_record_summary.wrong_ans,
                        "skipped": test_record_summary.skipped_qns,
                        "attempted": test_record_summary.correct_ans+test_record_summary.wrong_ans
                    }
                    return {"status": True, "message": summary}
            else:
                return {"status": False, "message": "Something went wrong."}
        else:
            return {"status": False, "message": "Something went wrong."}

    except Exception as ex:
        return JSONResponse({"message": str(ex)}, status_code=208, )


@router.post('/submit_test_series_result/')
async def test_series_result(cid: str = Form(...), tid: str = Form(...), answer_state_data: str = Form(...), user=Depends(get_current_user)):
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            test_series_instance = await CourseCategoryTestSeries.get(id=tid)

            if await StudentTestSeriesRecord.exists(
                    student=student_instance,
                    test_series=test_series_instance):
                test_record_summary = await StudentTestSeriesRecord.filter(student=student_instance,
                                                                           test_series=test_series_instance).update(test_record_summary=answer_state_data)

            return RedirectResponse(url="/student/test/result/"+cid+"/"+tid+"/", status_code=status.HTTP_302_FOUND)
        else:
            return JSONResponse({"status": False, "message": "Authentication failed."})

    except Exception as e:
        return JSONResponse({"status": False, "message": str(e)})


@router.get('/student/test/result/{cid}/{tid}/')
async def view_result(request: Request, cid: str, tid: str, user=Depends(get_current_user)):

    global summary, state_summary
    try:
        check = await authenticate_student_subscription(cid=cid, user=user)
        if check:
            student_instance = await Student.get(id=user)
            if await CourseCategoryTestSeries.exists(id=tid):
                test_series_instance = await CourseCategoryTestSeries.get(id=tid)
                title = test_series_instance.title
                test_series_qstns = await CourseCategoryTestSeriesQuestions.filter(
                    test_series=test_series_instance)

                student_instance = await Student.get(id=user)
                if await StudentTestSeriesRecord.exists(
                        student=student_instance,
                        test_series=test_series_instance):
                    test_record_summary = await StudentTestSeriesRecord.get(student=student_instance,
                                                                            test_series=test_series_instance)

                    state_summary = np.array(json.loads(
                        test_record_summary.test_record_summary))

                    summary = {
                        "correct": test_record_summary.correct_ans,
                        "wrong": test_record_summary.wrong_ans,
                        "skipped": test_record_summary.skipped_qns,
                        "not_attempted": len(test_series_qstns)-(test_record_summary.correct_ans+test_record_summary.wrong_ans)
                    }
                    question_state = []

                    for i in range(len(test_series_qstns)):
                        def get_state_summary(option, curr_stat):
                            flag2 = "text-white"
                            if curr_stat == option:
                                flag1 = "bg-danger"
                                if curr_stat == test_series_qstns[i].answer:
                                    flag1 = "bg-success"
                            else:
                                flag2 = ''
                                flag1 = ''
                                if option == test_series_qstns[i].answer:
                                    flag2 = "text-white"
                                    flag1 = "bg-success"

                            return flag2, flag1

                        opt_arr = np.array(
                            ["opt_1", "opt_2", "opt_3", "opt_4"])
                        opt_dict = {}
                        for x in opt_arr:
                            if (i + 1) <= len(state_summary):
                                if state_summary[i]:
                                    resp = get_state_summary(
                                        x, state_summary[i])

                                else:
                                    resp = get_state_summary(x, None)

                            else:
                                resp = get_state_summary(x, None)

                            opt_dict.update({x: resp})
                        question_state.append(opt_dict)

                return templates.TemplateResponse('testseries_result.html',
                                                  context={'request': request,
                                                           'student': student_instance,
                                                           'cid': cid,
                                                           'tid': tid,
                                                           'summary': summary,
                                                           "test_series_qstns": test_series_qstns,
                                                           "state_summary": state_summary,
                                                           "question_state": question_state,
                                                           "title": title

                                                           })
            else:
                return {"status": False, "message": "Something went wrong."}
        else:
            return {"status": False, "message": "Something went wrong."}

    except Exception as ex:
        return JSONResponse({"message": str(ex)}, status_code=208, )
