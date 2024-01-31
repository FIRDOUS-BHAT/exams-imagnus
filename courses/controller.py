import time
import os
import logging
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional
import boto3
from fastapi.encoders import jsonable_encoder
import pytz
import razorpay
import requests
from botocore.client import Config
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette import status
from starlette.responses import JSONResponse, RedirectResponse, Response
from tortoise.contrib.fastapi import HTTPNotFoundError

from FCM.route import push_service
from admin_dashboard.models import (
    Course_Pydantic,
    CourseCart,
    CourseCategoryLectures,
    CurrentAffairs,
    Instructor,
    Instructor_Pydantic,
    Course,
    CourseCategories,
    CourseCategories_Pydantic,
    CourseSubscriptionPlans_Pydantic,
    CourseSubscriptionPlans,
    Preference,
)
from checkout.apis.route import confirmOrderPydantic, place_free_subscription
from checkout.models import PaymentRecords, PaymentRecords_Pydantic, paymentSession
from configs import appinfo
from student.controller import get_current_user
from student.models import Student
from student_choices.models import (
    StudentChoice_Pydantic,
    StudentChoices,
    activeSubscription,
)
from study_material.models import (
    StudyMaterialCategories,
    StudyMaterialOrderInstance,
    StudyMaterialOrderInstance_Pydantic,
    StudyMaterialOrderItems,
    StudyMaterialOrderItems_Pydantic,
    TestSeriesOrders,
    TestSeriesOrders_Pydantic,
)

tz = pytz.timezone("Asia/Kolkata")
updated_at = datetime.now(tz)


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()

app_name = settings.app_name
app_version = settings.app_version
razorpay_key = settings.razorpay_key
razorpay_secret = settings.razorpay_secret

client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
client.set_app_details({"title": app_name, "version": app_version})

router = APIRouter()

app = FastAPI()
templates = Jinja2Templates(directory="courses/templates/")


@router.get(
    "/student/courses/{preference_slug}/",
)
async def courses(request: Request, preference_slug: str, _=Depends(get_current_user)):
    try:
        # courses_obj = await Preference_Pydantic.from_queryset_single(Preference.get(slug=preference_slug))
        courses_obj = await Course_Pydantic.from_queryset(
            Course.filter(preference__slug=preference_slug)
        )
        # return courses_obj
        new_list = []
        for course in courses_obj:
            new_dict = course.dict()
            purchased_count = await StudentChoices.filter(course__id=course.id).count()
            new_dict.update({"enrolled_students": purchased_count})
            new_list.append(new_dict)
        return templates.TemplateResponse(
            "courses.html",
            context={
                "request": request,
                "preference_slug": preference_slug,
                "courses": new_list,
            },
        )
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.get("/student/courses/")
async def get_courses():
    try:
        preference = await Preference.first()

        return preference
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.get(
    "/student/preference/",
)
async def courses(request: Request, _=Depends(get_current_user)):
    """Get all preference with their courses"""
    try:
        # courses_obj = await Preference_Pydantic.from_queryset_single(Preference.get(slug=preference_slug))

        # return courses_obj
        preference_list = []

        preferences = await Preference.all().order_by("display_order")
        for preference in preferences:
            new_list = []
            new_pref = jsonable_encoder(preference)
            courses_obj = await Course.filter(preference__id=preference.id)
            for course in courses_obj:
                new_dict = jsonable_encoder(course)
                # new_dict = course
                purchased_count = await StudentChoices.filter(
                    course__id=course.id
                ).count()
                new_dict.update({"enrolled_students": purchased_count})
                new_list.append(new_dict)
            new_pref.update({"courses": new_list})
            preference_list.append(new_pref)

        return templates.TemplateResponse(
            "new_course_preference.html",
            context={
                "request": request,
                "preferences": preferences,
                "preference_list": preference_list,
            },
        )
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.get(
    "/student/course_details/{p_slug}/{c_slug}/",
    # response_model=CourseCategoriesPydantic
)
async def course_details(
    request: Request, p_slug: str, c_slug: str, user=Depends(get_current_user)
):
    try:
        course = await Course.get(slug=c_slug)
        user_id = await Student.get(id=user)
        course_cat_obj = await CourseCategories_Pydantic.from_queryset(
            CourseCategories.filter(course=course)
        )
        instructors = await Instructor_Pydantic.from_queryset(Instructor.all())
        subscription = (
            await CourseSubscriptionPlans.filter(course=course)
            .order_by("plan_price")
            .limit(1)
        )
        plan_price = subscription[0].plan_price

        enrolled = await StudentChoices.filter(course=course).count()
        if course_cat_obj[0].course.course_overview:
            overview = course_cat_obj[0].course.course_overview[0]
        else:
            overview = None
        lecture_count = await CourseCategoryLectures.filter(
            category_topic__category__course=course
        ).count()
        course_name = course_cat_obj[0].course.name

        return templates.TemplateResponse(
            "course_details.html",
            context={
                "request": request,
                "overview": overview,
                "course_name": course_name,
                "course_objs": course_cat_obj,
                "c_slug": c_slug,
                "student_name": user_id.fullname,
                "plan_price": plan_price,
                "instructors": instructors,
                "enrolled": enrolled,
                "lecture_count": lecture_count,
                #    'course_lec_obj': course_lec_obj,
            },
        )
    except Exception as ex:
        return RedirectResponse(
            url="/student/login/", status_code=status.HTTP_302_FOUND
        )
        # return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get("/students/subscription_plans/course/{course_slug}/")
async def subscription_plans_page(
    request: Request, course_slug: str, _=Depends(get_current_user)
):
    try:
        c_obj = await Course.get(slug=course_slug)
        course_plans = await CourseSubscriptionPlans_Pydantic.from_queryset(
            CourseSubscriptionPlans.filter(is_active=True, course=c_obj).order_by(
                "plan_price"
            )
        )
        return templates.TemplateResponse(
            "subscription.html", context={"request": request, "plans": course_plans}
        )
    except Exception as e:
        return RedirectResponse(
            url="/student/login/", status_code=status.HTTP_302_FOUND
        )


@router.get("/students/subscription_plan/{subscrip_id}/checkout/")
async def checkout_page(
    request: Request,
    subscrip_id: str,
    user: str = Depends(get_current_user),
):
    try:
        txnid = uuid.uuid1()
        pay_obj = await paymentSession.exists(txn_id=txnid)
        if not pay_obj:
            await paymentSession.create(txn_id=txnid, student=user)
        student_ins = await Student.get(id=user)
        subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id)
        price = subs_obj.plan_price
        course = await Course.get(id=subs_obj.course_id)
        course_obj = {
            "id": course.id,
            "name": course.name,
            "slug": course.slug,
            "web_icon": course.web_icon,
        }
        subscription = {
            "course": course_obj,
            "plan_price": subs_obj.plan_price,
        }
        if await CourseCart.exists(student=student_ins):
            await CourseCart.filter(student=student_ins).delete()
            await CourseCart.create(student=student_ins, subscription=subs_obj)
        else:
            await CourseCart.create(student=student_ins, subscription=subs_obj)
        # return subs_obj
        student_id = student_ins.id
        return templates.TemplateResponse(
            "checkout.html",
            context={
                "request": request,
                "subscrip_price": price,
                "student": student_ins,
                "subscrip_id": subscrip_id,
                "txnid": txnid,
                "razorpay_key": razorpay_key,
                "student_name": student_ins.fullname,
                "email": student_ins.email,
                "mobile": student_ins.mobile,
                "subscription": subscription,
                "student_id": student_id,
            },
        )
    except Exception as exc:
        return RedirectResponse(
            url="/student/login/", status_code=status.HTTP_302_FOUND
        )

        # return Response(str(exc), status_code=208)


@router.get(
    "/student/my-account/",
)
async def my_account(request: Request, user: str = Depends(get_current_user)):
    try:
        student_ins = await Student.exists(id=user)
        if not student_ins:
            return RedirectResponse(
                url="/student/login/", status_code=status.HTTP_302_FOUND
            )
        student_ins = await Student.get(id=user)

        return templates.TemplateResponse(
            "my-account.html",
            context={
                "request": request,
                "student": student_ins,
            },
        )
    except Exception as ex:
        #   return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)
        return RedirectResponse(
            url="/student/login/", status_code=status.HTTP_302_FOUND
        )


@router.get("/student/new-dashboard/", responses={404: {"model": HTTPNotFoundError}})
async def student_dashboard(request: Request, user=Depends(get_current_user)):
    # try:
    
    course_exist = await PaymentRecords.exists(student__id=user)
    course_count = 0
    std_m_count = 0
    test_series_count = 0
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)

    if course_exist:
        course_count = await PaymentRecords.filter(student__id=user).count()
        # subscriptions = await StudentChoice_Pydantic.from_queryset(
        #     StudentChoices.filter(student__id=user, expiry_date__gte=now)
        # )
        subscriptions = await StudentChoices.filter(
            student__id=user, expiry_date__gte=now
        ).values(
            subscription_id="subscription__id",
            web_icon="course__web_icon",
            preference_name="course__preference__name",
            course_name="course__name",
            plan_price="subscription__plan_price",
            course_id="course__id",
            payment_status="payment__payment_status",
        )
    else:
        subscriptions = None
    std_m_exist = await StudyMaterialOrderInstance.exists(
        student__id=user, package_mode=1
    )
    if await StudyMaterialOrderInstance.exists(student__id=user, package_mode=1):
        std_m_count = await StudyMaterialOrderInstance.filter(student__id=user).count()
        # std_m = await StudyMaterialOrderInstance_Pydantic.from_queryset(
        #     StudyMaterialOrderInstance.filter(student__id=user)
        # )
        std_m = await StudyMaterialOrderItems.filter(order__student__id=user).values(
            web_icon="item_id__web_icon",
            course_title="item_id__name",
            discount_price="item_id__discount_price",
        )

    elif await StudyMaterialOrderInstance.exists(student__id=user, package_mode=2):
        std_m_count = await StudyMaterialOrderInstance.filter(student__id=user).count()
        # std_m = await StudyMaterialOrderInstance_Pydantic.from_queryset(
        #     StudyMaterialOrderInstance.filter(student__id=user)
        # )
        std_m = await StudyMaterialOrderItems.filter(order__student__id=user).values(
            web_icon="item_id__web_icon",
            course_title="item_id__name",
            discount_price="item_id__discount_price",
        )

    else:
        std_m = None
    test_series = await TestSeriesOrders.exists(student__id=user)
    if test_series:
        test_series_count = await TestSeriesOrders.filter(student__id=user).count()
        testseries = await TestSeriesOrders.filter(student__id=user).values(
            "razorpay_order_id",
            "razorpay_payment_id",
            "bill_amount",
            "created_at",
            student_fullname="student__fullname",
            student_mobile="student__mobile",
            test_series_course_preference_name="test_series__course__preference__name",
            test_series_course_name="test_series__course__name",
            test_series_web_icon="test_series__web_icon",
        )

    else:
        testseries = None
    total_order_count = course_count + std_m_count + test_series_count
    if course_exist or std_m_exist:
        # return std_m
        return templates.TemplateResponse(
            "new-dashboard.html",
            context={
                "request": request,
                "total_order_count": total_order_count,
                "subscription_count": course_count,
                "std_m_count": std_m_count,
                "subscriptions": subscriptions,
                "std_ms": std_m,
                "testseries": testseries,
            },
        )
    else:
        return templates.TemplateResponse(
            "new-dashboard.html",
            context={
                "request": request,
                "total_order_count": total_order_count,
                "subscription_count": course_count,
                "std_m_count": std_m_count,
                "subscriptions": subscriptions,
                "std_ms": std_m,
            },
        )
    # except Exception as ex:

    #     return JSONResponse({'status': False, 'message': str(ex)}, status_code=500)
    # return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.get(
    "/student/my-purchases/",
)
async def my_account(request: Request, user: str = Depends(get_current_user)):
    try:
        student_ins = await Student.exists(id=user)
        if not student_ins:
            return RedirectResponse(
                url="/student/login/", status_code=status.HTTP_302_FOUND
            )
        student_ins = await Student.get(id=user)

        return templates.TemplateResponse(
            "my_purchases.html",
            context={
                "request": request,
                "student": student_ins,
            },
        )
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.get(
    "/student/my-orders/",
)
async def my_account(request: Request, user: str = Depends(get_current_user)):
    try:
        student_ins = await Student.exists(id=user)
        if not student_ins:
            return RedirectResponse(
                url="/student/login/", status_code=status.HTTP_302_FOUND
            )
        student_ins = await Student.get(id=user)

        if await PaymentRecords.exists(student=student_ins):
            orders = await PaymentRecords_Pydantic.from_queryset(
                PaymentRecords.filter(student=student_ins).order_by("-created_at")
            )
        else:
            orders = None

        if await StudyMaterialOrderInstance.exists(student=student_ins):
            std_m_orders = await StudyMaterialOrderItems_Pydantic.from_queryset(
                StudyMaterialOrderItems.filter(order__student=student_ins).order_by(
                    "-created_at"
                )
            )
        else:
            std_m_orders = None
            # return orders
        return templates.TemplateResponse(
            "my-orders.html",
            context={
                "request": request,
                "student": student_ins,
                "orders": orders,
                "stdMaterialOrders": std_m_orders,
            },
        )
    except Exception as ex:
        #   return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)
        return RedirectResponse(
            url="/student/login/", status_code=status.HTTP_302_FOUND
        )


aws_access_key_id = settings.AWS_SERVER_PUBLIC_KEY
aws_secret_access_key = settings.AWS_SERVER_SECRET_KEY
aws_region = settings.AWS_SERVER_REGION


@router.post(
    "/study_material_url/",
)
async def get_signed_url(request: Request, user: str = Depends(get_current_user)):
    try:
        data = await request.json()
        if await StudyMaterialOrderItems.exists(
            order__student__id=user, id=data["mid"]
        ):
            ord_instance = await StudyMaterialOrderItems.get(id=data["mid"]).values(
                "item_id__id"
            )
            material_id = ord_instance["item_id__id"]

            material_instance = await StudyMaterialCategories.get(id=material_id)
            material_url_key = material_instance.material_url_key

            s3Client = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                config=Config(signature_version="s3v4"),
                region_name=aws_region,
            )
            presigned_url = s3Client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": "testing-bucket-s3-uploader",
                    "Key": material_url_key,
                },
                ExpiresIn=600,
            )

            #########################
            r = requests.get(presigned_url, stream=True)

            #########################

            return JSONResponse(
                {
                    "status": True,
                    "message": presigned_url,
                    "material_url_key": material_url_key,
                }
            )
        else:
            return JSONResponse({"status": False, "message": "Wrong Input"})
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)})


@router.post("/delete_old_s3_objects")
async def delete_old_s3_objects():
    try:
        # Define the threshold (60 days in this case)
        threshold = datetime.now() - timedelta(days=60)

        s3 = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name=aws_region,
        )

        folder_name = "transcoded/"

        # List and check each object in the bucket
        print("S3 RESPONSE")

        continuation_token = None
        while True:
            list_params = {
                "Bucket": "testing-bucket-s3-uploader",
                "Prefix": folder_name,
            }

            if continuation_token:
                list_params["ContinuationToken"] = continuation_token

            response = s3.list_objects_v2(**list_params)

            # print(response)

            if "Contents" in response:
                print("===========RESPONSE CONTENTS==============")
                print(response["Contents"])
                for item in response["Contents"]:
                    print(f'========{item["Key"]}========')
                    last_accessed = item["LastAccessedTime"]
                    if last_accessed < threshold:
                        print(f"Deleting {item['Key']}...")

                        # s3.delete_object(Bucket='testing-bucket-s3-uploader', Key=item['Key'])
            else:
                print("No objects in bucket.")

            if response.get("IsTruncated"):  # True if there are more results available
                continuation_token = response.get("NextContinuationToken")
            else:
                break
    except Exception as ex:
        print(str(ex))
        return str(ex)


"""'Sample progress bar file here"""


@router.get(
    "/student/download-progress-bar/",
)
async def download_progress_bar(
    request: Request,
):
    return templates.TemplateResponse(
        "sample-file-progress-bar.html",
        context={
            "request": request,
        },
    )


async def get_razorpay_order_id(amount, subscription_id):
    try:
        print("YOU ARE IN GET RAZORPAY ORDER ID")
        # TAKE ONLY LAST 10 CHARACTER OF THE SUBSCRIPTION ID FOR RECEITP ID
        receipt_id = str(subscription_id)[-10:]

        order = client.order.create(
            {
                "amount": amount * 100,
                "currency": "INR",
                "receipt": f"order_rcptid_{receipt_id}",
            }
        )
        order_id = order["id"]
        return order_id
    except Exception as ex:
        print(str(ex))
        return None


async def create_subscription(student, item_instance, now_date):
    """Create subscription for student"""
    try:
        print("YOU ARE IN CREATE SUBSCRIPTION")
        amount = item_instance.plan_price
        validity = item_instance.validity
        expiry_date = now_date + relativedelta(months=validity)

        print(await get_razorpay_order_id(amount, item_instance.id))

        order_id = await get_razorpay_order_id(amount, item_instance.id)

        if not order_id:
            return False, None

        print(f"{order_id} is the order id")

        payment_obj = await PaymentRecords.create(
            student=student,
            payment_mode=1,
            subscription=item_instance,
            payment_id="",
            order_id=order_id,
            coupon="",
            coupon_discount=0,
            bill_amount=amount,
            gateway_name="Razorpay",
            payment_status=1,
            source="web",
            updated_at=now_date,
            created_at=now_date,
        )

        if payment_obj:
            print("PAYMENT OBJECT CREATED")

            c_ins = await Course.get(id=item_instance.course_id)

            student_choices_obj = await StudentChoices.create(
                student=student,
                course=c_ins,
                subscription=item_instance,
                payment=payment_obj,
                subscription_duration=validity,
                expiry_date=expiry_date,
                updated_at=now_date,
                created_at=now_date,
            )
            if student_choices_obj:
                if await activeSubscription.exists(student=student, course=c_ins):
                    await activeSubscription.filter(
                        student=student, course=c_ins
                    ).delete()
                    await activeSubscription.create(
                        student=student,
                        payment=payment_obj,
                        subscription=item_instance,
                        course=c_ins,
                        updated_at=now_date,
                    )
                else:
                    await activeSubscription.create(
                        student=student,
                        payment=payment_obj,
                        subscription=item_instance,
                        course=c_ins,
                        updated_at=now_date,
                    )

                return True, order_id
        return False, None
    except Exception as ex:
        print(f"{str(ex)} IN CREATE SUBSCRIPTION")
        return False, None


@router.post("/course/create_order/")
async def create_razorpay_order(
    create_order: Optional[str] = None, user=Depends(get_current_user)
):
    """create order"""
    try:
        now = datetime.now(tz)
        student = await Student.get(id=user)
        if await CourseCart.exists(student=student):
            cart_instance = await CourseCart.get(student=student).values(
                "subscription__id"
            )
            item_id = cart_instance["subscription__id"]
            item_instance = await CourseSubscriptionPlans.get(id=item_id)
            amount = item_instance.plan_price
            # await StudyMaterialOrderInstance.filter(student=student, item_id=item_instance).delete()

            if create_order == "True":
                # CASE 1: IF STUDENT IS ALREADY SUBSCRIBED TO A PLAN
                if await StudentChoices.exists(
                    student=student,
                    subscription=item_instance,
                    expiry_date__gte=now,
                    payment__payment_status=2,
                ):
                    return JSONResponse(
                        {
                            "status": False,
                            "message": "you're already registered with this plan",
                        },
                        status_code=200,
                    )

                # CASE 2: IF STUDENT IS ALREADY PLACED THE ORDER BUT PAYMENT IS PENDING
                elif await StudentChoices.exists(
                    student=student,
                    subscription=item_instance,
                    payment__payment_status=1,
                ):
                    # delete from student choices
                    if await StudentChoices.get(
                        student=student, subscription=item_instance
                    ).delete():
                        # delete from active subscription
                        if await activeSubscription.get(
                            student=student, subscription=item_instance
                        ).delete():
                            # delete it from payment records table
                            await PaymentRecords.get(
                                student=student,
                                subscription=item_instance,
                                payment_status=1,
                            ).delete()

                flag, order_id = await create_subscription(student, item_instance, now)

                if flag:
                    return JSONResponse(
                        {"status": True, "order_id": order_id, "amount": amount},
                        status_code=200,
                    )

                return JSONResponse(
                    {"status": False, "message": "Something went wrong"},
                    status_code=208,
                )

        else:
            return JSONResponse(
                {"status": False, "details": "Cart is Empty"}, status_code=208
            )

    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


async def razorpay_signature_verification(order_id, payment_id, signature):
    is_valid_signature = client.utility.verify_payment_signature(
        {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
    )

    if is_valid_signature:
        return True
    return False


@router.post("/course/confirm_order/")
async def confirm_order(request: Request, user=Depends(get_current_user)):
    try:
        data = await request.json()
        student = await Student.get(id=user)
        order_id = data["order_id"]
        payment_id = data["payment_id"]
        payment_signature = data["signature"]

        # now verify this razorpay signature

        sig_resp = await razorpay_signature_verification(
            order_id=order_id, payment_id=payment_id, signature=payment_signature
        )

        if not sig_resp:
            return JSONResponse(
                {"status": False, "message": "Something went wrong"}, status_code=208
            )

        # time.sleep(1.5)

        if await PaymentRecords.exists(order_id=data["order_id"]):
            print("YOU ARE HERE")
            await PaymentRecords.filter(order_id=data["order_id"]).update(
                payment_id=data["payment_id"], payment_status=2, updated_at=updated_at
            )
            print("YOU ARE HERE 1 payment records updated")

            subscription_validity = await PaymentRecords.get(order_id=order_id).values(
                "subscription__validity"
            )
            validity = subscription_validity["subscription__validity"]

            print(updated_at)
            expiry_date = updated_at + relativedelta(months=validity)

            # update expiry date of student choices
            # Fetch the IDs
            ids_to_update = await StudentChoices.filter(
                student=student, payment__order_id=order_id
            ).values_list("id", flat=True)

            # Perform the update
            await StudentChoices.filter(id__in=ids_to_update).update(
                expiry_date=expiry_date, updated_at=updated_at
            )

            print("YOU ARE HERE 2 student choices updated")

            course_id = await PaymentRecords.get(order_id=order_id).values(
                "subscription__course__id"
            )

            subscription_id = await PaymentRecords.get(order_id=order_id).values(
                "subscription__id"
            )

            subscription_id = subscription_id["subscription__id"]

            await place_free_subscription(subscription_id, user)

            print("free subscription called")

            course_id = course_id["subscription__course__id"]

            c_ins = await Course.get(id=course_id)

            # delete coursecart
            await CourseCart.filter(
                student=student, subscription_id=subscription_id
            ).delete()

            fcm_token = student.fcm_token
            if fcm_token:
                message_title = "Payment successful"
                message_body = (
                    "You have successfully purchased the "
                    + c_ins.name
                    + " course.\n\nHappy Learning"
                )
                data_message = {"open": "profile", "data_payload": {}}

                # fire notification to student
                push_service.notify_single_device(
                    registration_id=fcm_token,
                    message_title=message_title,
                    message_body=message_body,
                    data_message=data_message,
                )

            resp = JSONResponse(
                {
                    "status": True,
                    "redirectUrl": "/student/new-dashboard/",
                    "message": "Order confirmed",
                },
                status_code=200,
            )

        else:
            resp = JSONResponse(
                {"status": False, "message": "Something went wrong"}, status_code=208
            )

        return resp

    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.post(
    "/course/place_order/",
)
async def place_order(request: Request, uid=Depends(get_current_user)):
    try:
        data = await request.json()
        params_dict = data
        razorpay_verify = client.utility.verify_payment_signature(params_dict)

        if await Student.exists(id=uid):
            user_obj = await Student.get(id=uid)
            cart = await CourseCart.get(student=user_obj).values("subscription__id")
            subscrip_id = cart["subscription__id"]
            user_obj = await Student.get(id=uid)
            payment_id = data["razorpay_payment_id"]

            if await CourseSubscriptionPlans.exists(id=subscrip_id):
                subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values(
                    "course__id", "validity"
                )
                subs_obj1 = await CourseSubscriptionPlans.get(id=subscrip_id)

                cid = subs_obj["course__id"]
                validity = subs_obj["validity"]
                c_ins = await Course.get(id=cid)

                """check if any subscription"""

                new_validity = 0
                new_price = 0
                existing_validity = 0
                existing_price = 0
                used_months = 0
                now = datetime.now(tz)
                if await StudentChoices.exists(
                    student=user_obj, course=c_ins, expiry_date__gte=now
                ):
                    subscribed_obj = await StudentChoices.get(
                        student=user_obj, course=c_ins, expiry_date__gte=now
                    ).values("subscription__id")
                    subscription_id = subscribed_obj["subscription__id"]
                    ex_subscript_obj = await CourseSubscriptionPlans.get(
                        id=subscription_id
                    )
                    existing_validity = ex_subscript_obj.validity

                    if existing_validity and (validity > existing_validity):
                        subscribed_plan_obj = await StudentChoices.get(
                            student=user_obj, course=c_ins, expiry_date__gte=now
                        )

                        delta = now - subscribed_plan_obj.created_at
                        used_months = round(delta.days / 30)
                        validity = validity - used_months

                        payment_obj = await PaymentRecords.create(
                            student=user_obj,
                            payment_mode=data["payment_mode"],
                            subscription=subs_obj1,
                            payment_id=payment_id,
                            order_id=data["order_id"],
                            coupon=data["coupon"],
                            coupon_discount=data["coupon_discount"],
                            bill_amount=data["bill_amount"],
                            gateway_name="Razorpay",
                            updated_at=updated_at,
                            created_at=updated_at,
                        )

                        await StudentChoices.filter(
                            student=user_obj, course=c_ins
                        ).update(
                            subscription=subs_obj1,
                            payment=payment_obj,
                            expiry_date=now,
                            updated_at=updated_at,
                        )

                        await activeSubscription.filter(
                            student=user_obj, course=c_ins
                        ).update(
                            subscription=subs_obj1,
                            payment=payment_obj,
                            updated_at=updated_at,
                        )

                elif not await StudentChoices.exists(
                    course=c_ins, student=user_obj, expiry_date__gte=now
                ):
                    payment_obj = await PaymentRecords.create(
                        student=user_obj,
                        payment_mode=1,
                        subscription=subs_obj1,
                        payment_id=payment_id,
                        order_id=data["razorpay_order_id"],
                        coupon=data["coupon"],
                        coupon_discount=data["coupon_discount"],
                        bill_amount=data["bill_amount"],
                        gateway_name="Razorpay",
                        updated_at=updated_at,
                        created_at=updated_at,
                    )

                    expiry_date = updated_at + relativedelta(months=validity)
                    if payment_obj:
                        student_choices_obj = await StudentChoices.create(
                            student=user_obj,
                            course=c_ins,
                            subscription=subs_obj1,
                            payment=payment_obj,
                            subscription_duration=validity,
                            expiry_date=expiry_date,
                            updated_at=updated_at,
                            created_at=updated_at,
                        )
                        if student_choices_obj:
                            if await activeSubscription.exists(
                                student=user_obj, course=c_ins
                            ):
                                await activeSubscription.filter(
                                    student=user_obj, course=c_ins
                                ).delete()
                                await activeSubscription.create(
                                    student=user_obj,
                                    payment=payment_obj,
                                    subscription=subs_obj1,
                                    course=c_ins,
                                    updated_at=updated_at,
                                )
                            else:
                                await activeSubscription.create(
                                    student=user_obj,
                                    payment=payment_obj,
                                    subscription=subs_obj1,
                                    course=c_ins,
                                    updated_at=updated_at,
                                )

                            fcm_token = user_obj.fcm_token
                            if fcm_token:
                                message_title = "Payment successful"
                                message_body = (
                                    "You have successfully purchased the "
                                    + c_ins.name
                                    + " course.\n\nHappy Learning"
                                )
                                data_message = {"open": "profile", "data_payload": {}}
                                result = push_service.notify_single_device(
                                    registration_id=fcm_token,
                                    message_title=message_title,
                                    message_body=message_body,
                                    data_message=data_message,
                                )
                            return JSONResponse(
                                {
                                    "status": True,
                                    "message": "order placed successfully",
                                },
                                status_code=200,
                            )
                        else:
                            return JSONResponse(
                                {"status": False, "message": "Something went wrong"},
                                status_code=208,
                            )

                else:
                    return JSONResponse(
                        {
                            "status": False,
                            "message": "you're already registered with this plan",
                        },
                        status_code=208,
                    )

    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.get("/m/current_affairs")
async def get_current_monthly_affairs(request: Request):
    current_affairs = await CurrentAffairs.all().distinct().values("month_year")
    return templates.TemplateResponse(
        "current_affairs_month.html",
        context={"request": request, "current_affairs": current_affairs},
    )


@router.get("/{month}/current_affairs")
async def get_current_affairs(request: Request, month: str):
    current_affairs = await CurrentAffairs.filter(month_year=month)
    # return current_affairs
    return templates.TemplateResponse(
        "current_affairs.html",
        context={
            "request": request,
            "current_affairs": current_affairs,
            "month": month,
        },
    )
