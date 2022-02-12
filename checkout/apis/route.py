from functools import lru_cache
from aiohttp import RequestInfo
from fastapi_pagination import request
import razorpay
from fastapi.encoders import jsonable_encoder
import httpx
import uuid
from datetime import datetime
from typing import List, Optional
import pytz
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, validator
from starlette.responses import JSONResponse
from FCM.route import push_service
from admin_dashboard.models import CourseSubscriptionPlans, Course
from checkout.models import PaymentRecordsIn_Pydantic, PaymentRecords, PaymentRecords_Pydantic
from configs import appinfo
from student.apis.pydantic_models import SubscriptionPlanPydantic
from student.models import Student
from student_choices.models import StudentChoices, activeSubscription
from study_material.models import StudyMaterialCategories, StudyMaterialCourse, StudyMaterialOrderInstance, StudyMaterialOrderItems, TestSeriesOrders
from utils.util import get_current_user

router = APIRouter()

tz = pytz.timezone('Asia/Kolkata')
updated_at = datetime.now(tz)


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()


razorpay_key = settings.razorpay_key
razorpay_secret = settings.razorpay_secret

client = razorpay.Client(auth=(razorpay_key, razorpay_secret))


class manualOrderPydantic(BaseModel):
    mobile: List[str]
    subscription_id: str
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    gateway_name: Optional[str] = None
    coupon: Optional[str] = None
    coupon_discount: Optional[int] = None
    bill_amount: Optional[int] = None


@router.post('/place_manual_order', )
async def place_manual_order(data: manualOrderPydantic, _=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)

        response = []
        error_response = []

        for uid in data.mobile:

            if await Student.exists(mobile=uid):
                user_obj = await Student.get(mobile=uid)
                subscrip_id = data.subscription_id
                if await CourseSubscriptionPlans.exists(id=subscrip_id):
                    subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values("course__id", "validity")
                    subs_obj1 = await CourseSubscriptionPlans.get(id=subscrip_id)

                    if not await PaymentRecords.exists(subscription=subs_obj1, student=user_obj):
                        payment_id = data.payment_id

                        gateway_name = data.gateway_name
                        cid = subs_obj["course__id"]
                        validity = subs_obj["validity"]
                        # async for team in subs_obj.course:
                        #     if team[0] == 'id':
                        #         cid = team[1]
                        #         break
                        c_ins = await Course.get(id=cid)
                        payment_obj = await PaymentRecords.create(
                            student=user_obj,
                            subscription=subs_obj1,
                            payment_id=payment_id,
                            order_id=data.order_id,
                            coupon=data.coupon,
                            coupon_discount=data.coupon_discount,
                            bill_amount=data.bill_amount,
                            gateway_name='Razorpay',
                            updated_at=updated_at,
                            created_at=updated_at
                        )
                        datetime_1 = datetime.now(tz)
                        expiry_date = datetime_1 + \
                            relativedelta(months=validity)
                        if payment_obj:
                            student_choices_obj = await StudentChoices.create(
                                student=user_obj,
                                course=c_ins,
                                subscription=subs_obj1,
                                payment=payment_obj,
                                subscription_duration=validity,
                                expiry_date=expiry_date,
                                updated_at=updated_at,
                                created_at=updated_at
                            )
                            if student_choices_obj:
                                if await activeSubscription.exists(student=user_obj, course=c_ins):
                                    await activeSubscription.filter(
                                        student=user_obj, course=c_ins).delete()
                                    await activeSubscription.create(
                                        student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                        course=c_ins, updated_at=datetime_1
                                    )
                                else:
                                    await activeSubscription.create(
                                        student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                        course=c_ins, updated_at=datetime_1
                                    )

                                fcm_token = user_obj.fcm_token
                                if fcm_token:
                                    message_title = 'Payment successful'
                                    message_body = "You have successfully purchased the " + \
                                        c_ins.name + " course.\n\nHappy Learning"
                                    data_message = {
                                        "open": "dashboard",
                                        "data_payload": {}
                                    }
                                    result = push_service.notify_single_device(
                                        registration_id=fcm_token, message_title=message_title,
                                        click_action="FLUTTER_NOTIFICATION_CLICK",
                                        message_body=message_body, data_message=data_message)
                                response.append(JSONResponse(
                                    {"status": True, "message": "order placed successfully for mobile number " + uid},
                                    status_code=200))
                            else:

                                response.append(JSONResponse(
                                    {"status": False,
                                        "message": "Something went wrong with mobile number " + uid},
                                    status_code=208))

                    else:
                        error_response.append(JSONResponse(
                            {"status": False,
                             "message": "This mobile number " + uid + " is already registered with this plan"},
                            status_code=208
                        ))

            else:
                error_response.append(JSONResponse(
                    {'error': 'This mobile number ' + uid + ' is not registered'}, status_code=208))
        return {"success": response, "error": error_response}
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208)


@router.post('/place_order', )
async def place_order(data: PaymentRecordsIn_Pydantic, _=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)
        now = datetime.now(tz)

        uid = data.student_id
        payment_id = data.payment_id
        payment_status = 1
        if payment_id:
            razorpay_resp = client.payment.fetch(data.payment_id)

            # print(razorpay_resp)
            print("========Razorpay status here=========================")

            if razorpay_resp and (not await PaymentRecords.exists(payment_id=payment_id)):
                payment_status = 2

        if await Student.exists(id=uid):
            user_obj = await Student.get(id=uid)
            subscrip_id = data.subscription_id

            if await CourseSubscriptionPlans.exists(id=subscrip_id):
                subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values("course__id", "validity")
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
                if await StudentChoices.exists(student=user_obj,
                                               course=c_ins, expiry_date__gte=now):

                    subscribed_obj = await StudentChoices.get(student=user_obj,
                                                              course=c_ins, expiry_date__gte=now).values("subscription__id")
                    subscription_id = subscribed_obj['subscription__id']
                    ex_subscript_obj = await CourseSubscriptionPlans.get(id=subscription_id)
                    existing_validity = ex_subscript_obj.validity

                    if existing_validity and (validity > existing_validity):
                        subscribed_plan_obj = await StudentChoices.get(student=user_obj,
                                                                       course=c_ins, expiry_date__gte=now)

                        delta = now - subscribed_plan_obj.created_at
                        used_months = round(delta.days / 30)
                        validity = validity - used_months

                        await StudentChoices.filter(student=user_obj, course=c_ins).update(expiry_date=now)

                if not await StudentChoices.exists(subscription=subs_obj1, student=user_obj, expiry_date__gte=now):

                    gateway_name = data.gateway_name

                    # async for team in subs_obj.course:
                    #     if team[0] == 'id':
                    #         cid = team[1]
                    #         break

                    # import pytz
                    # tz = pytz.timezone('Asia/Kolkata')

                    payment_obj = await PaymentRecords.create(
                        student=user_obj,
                        payment_mode=data.payment_mode,
                        subscription=subs_obj1,
                        payment_id=payment_id,
                        order_id=data.order_id,
                        coupon=data.coupon,
                        coupon_discount=data.coupon_discount,
                        bill_amount=data.bill_amount,
                        gateway_name='Razorpay',
                        payment_status=payment_status,
                        updated_at=updated_at,
                        created_at=updated_at
                    )
                    datetime_1 = datetime.now(tz)
                    expiry_date = datetime_1 + relativedelta(months=validity)
                    if payment_obj:
                        student_choices_obj = await StudentChoices.create(
                            student=user_obj,
                            course=c_ins,
                            subscription=subs_obj1,
                            payment=payment_obj,
                            subscription_duration=validity,
                            expiry_date=expiry_date,
                            updated_at=updated_at,
                            created_at=updated_at
                        )
                        if student_choices_obj:
                            if await activeSubscription.exists(student=user_obj, course=c_ins):
                                await activeSubscription.filter(
                                    student=user_obj, course=c_ins).delete()
                                await activeSubscription.create(
                                    student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                    course=c_ins, updated_at=datetime_1
                                )
                            else:
                                await activeSubscription.create(
                                    student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                    course=c_ins, updated_at=datetime_1
                                )

                            fcm_token = user_obj.fcm_token
                            if fcm_token:
                                message_title = 'Payment successful'
                                message_body = "You have successfully purchased the " + \
                                               c_ins.name + " course.\n\nHappy Learning"
                                data_message = {
                                    "open": "profile",
                                    "data_payload": {}
                                }
                                result = push_service.notify_single_device(registration_id=fcm_token,
                                                                           message_title=message_title,
                                                                           message_body=message_body,
                                                                           data_message=data_message)
                            return JSONResponse(
                                {"status": True, "message": "order placed successfully"}, status_code=200)
                        else:

                            return JSONResponse(
                                {"status": False, "message": "Something went wrong"}, status_code=208)

                else:
                    return JSONResponse(
                        {"status": False,
                         "message": "you're already registered with this plan"},
                        status_code=208
                    )

    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208)


# return await PaymentRecords_Pydantic.from_tortoise_orm()


async def place_target_batch_orders(data):
    # try:
    updated_at = datetime.now(tz)
    now = datetime.now(tz)

    uid = data['student_id']

    if await Student.exists(id=uid):
        user_obj = await Student.get(id=uid)
        subscrip_id = data['subscription_id']
        payment_id = data['payment_id']

        if await CourseSubscriptionPlans.exists(id=subscrip_id):
            subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values("course__id", "validity")
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
            if await StudentChoices.exists(student=user_obj, course=c_ins, expiry_date__gte=now):

                subscribed_obj = await StudentChoices.get(student=user_obj,
                                                          course=c_ins, expiry_date__gte=now).values("subscription__id")
                subscription_id = subscribed_obj['subscription__id']
                ex_subscript_obj = await CourseSubscriptionPlans.get(id=subscription_id)
                existing_validity = ex_subscript_obj.validity

                if existing_validity and (validity > existing_validity):
                    subscribed_plan_obj = await StudentChoices.get(student=user_obj,
                                                                   course=c_ins, expiry_date__gte=now)

                    delta = now - subscribed_plan_obj.created_at
                    used_months = round(delta.days / 30)
                    validity = validity - used_months

                    payment_obj = await PaymentRecords.create(
                        student=user_obj,
                        payment_mode=data['payment_mode'],
                        subscription=subs_obj1,
                        payment_id=payment_id,
                        order_id=data['order_id'],
                        coupon=data['coupon'],
                        coupon_discount=data['coupon_discount'],
                        bill_amount=data['bill_amount'],
                        gateway_name='Razorpay',
                        updated_at=updated_at,
                        created_at=updated_at
                    )

                    await StudentChoices.filter(student=user_obj, course=c_ins).update(
                        subscription=subs_obj1, payment=payment_obj, expiry_date=now,
                        updated_at=updated_at)

                    await activeSubscription.filter(
                        student=user_obj, course=c_ins).update(
                            subscription=subs_obj1, payment=payment_obj, updated_at=updated_at)

            elif not await StudentChoices.exists(course=c_ins, student=user_obj, expiry_date__gte=now):

                gateway_name = data['gateway_name']

                # async for team in subs_obj.course:
                #     if team[0] == 'id':
                #         cid = team[1]
                #         break

                # import pytz
                # tz = pytz.timezone('Asia/Kolkata')

                payment_obj = await PaymentRecords.create(
                    student=user_obj,
                    payment_mode=data['payment_mode'],
                    subscription=subs_obj1,
                    payment_id=payment_id,
                    order_id=data['order_id'],
                    coupon=data['coupon'],
                    coupon_discount=data['coupon_discount'],
                    bill_amount=data['bill_amount'],
                    gateway_name='Razorpay',
                    updated_at=updated_at,
                    created_at=updated_at
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
                        created_at=updated_at
                    )
                    if student_choices_obj:
                        if await activeSubscription.exists(student=user_obj, course=c_ins):
                            await activeSubscription.filter(
                                student=user_obj, course=c_ins).delete()
                            await activeSubscription.create(
                                student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                course=c_ins, updated_at=updated_at
                            )
                        else:
                            await activeSubscription.create(
                                student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                course=c_ins, updated_at=updated_at
                            )

                        fcm_token = user_obj.fcm_token
                        if fcm_token:
                            message_title = 'Payment successful'
                            message_body = "You have successfully purchased the " + \
                                           c_ins.name + " course.\n\nHappy Learning"
                            data_message = {
                                "open": "profile",
                                "data_payload": {}
                            }
                            result = push_service.notify_single_device(registration_id=fcm_token,
                                                                       message_title=message_title,
                                                                       message_body=message_body,
                                                                       data_message=data_message)
                        return JSONResponse(
                            {"status": True, "message": "order placed successfully"}, status_code=200)
                    else:

                        return JSONResponse(
                            {"status": False, "message": "Something went wrong"}, status_code=208)

            else:
                return JSONResponse(
                    {"status": False,
                     "message": "you're already registered with this plan"},
                    status_code=208
                )


@router.get('/activeSubscriptions/{student_id}/{subscription_id}/')
async def active_subscription(student_id: str, subscription_id: str, _=Depends(get_current_user)):
    resp = await activeSubscription.filter(student=student_id)
    return resp


@router.get('/get_all_payment_records')
async def all_payment_records(_=Depends(get_current_user)):
    obj = await PaymentRecords.all()
    return obj


@router.get('/get_all_student_choices')
async def get_all_student_choices(_=Depends(get_current_user)):
    obj = await StudentChoices.all()
    return obj


# @router.delete('/delete_payment_record/{id}/')
# async def delete_payment_record(pid: str, _=Depends(get_current_user)):
#     obj = await PaymentRecords.filter(id=pid).delete()
#     return {"deleted"}


class PaymentHistoryPydantic(BaseModel):
    uid: uuid.UUID


class SubscriptionPydantic(BaseModel):
    id: uuid.UUID
    SubscriptionPlan: SubscriptionPlanPydantic
    validity: int
    plan_price: int


class OrderHistoryPydantic(BaseModel):
    id: uuid.UUID
    subscription: SubscriptionPydantic
    payment_id: Optional[str]
    created_at: datetime = None

    @validator('created_at', pre=True, always=True)
    def set_ts_now(cls, v):
        return v or datetime.now()


@router.post('/get_student_order_payment/',
             response_model=List[OrderHistoryPydantic]
             )
async def get_order_history(data: PaymentHistoryPydantic, _=Depends(get_current_user)):
    try:
        uid = data.uid
        if await Student.exists(id=uid):
            student_instance = await Student.get(id=uid)
            if await PaymentRecords.exists(student=student_instance):
                resp = await PaymentRecords_Pydantic.from_queryset(
                    PaymentRecords.filter(student=student_instance))
                return resp

    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


@router.post('/add_pre_target_batch_to_mains_students')
async def add_pre_target_batch_to_mains_students(_=Depends(get_current_user)):
    try:
        resp = []
        main_obj = await PaymentRecords.filter(
            subscription__id__in=['23438cf5-c964-425a-bf9d-82ee3a280e3e', '02177d58-6053-401b-bf9d-69b81f2ca510'])
        i = 0
        for order in main_obj:

            if await PaymentRecords.exists(student__id=order.student_id, subscription__id='baa368fb-388a-4e55-b52b-ae4fa70817c1'):
                # print(order.student_id)

                var = await PaymentRecords.filter(
                    student__id=order.student_id, subscription__id='baa368fb-388a-4e55-b52b-ae4fa70817c1'
                ).update(bill_amount='10')

                var_1 = var
                # data = {
                #     "payment_mode": 1,
                #     "payment_id": "",
                #     "order_id": "",
                #     "gateway_name": "",
                #     "coupon": "",
                #     "coupon_discount": 0,
                #     "bill_amount": 0,
                #     "student_id": order.student_id,
                #     "subscription_id": "baa368fb-388a-4e55-b52b-ae4fa70817c1"
                # }

                # res = await place_target_batch_orders(data)

                # async with httpx.AsyncClient() as client:
                #     content_obj = await client.post('https://exams.imagnus.in/api/place_order',
                #                                     json=jsonable_encoder(data))

                #     if content_obj.status_code == 200:
                #         resp.append(content_obj.json())
                i = i + 1
                res = {i+".updated"}
                resp.append(res)
            return resp

    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


class confirmOrderPydantic(BaseModel):
    identifier: str
    order_id: str
    payment_id: str
    signature:  Optional[str] = None


@router.post('/confirm_order')
async def confirm_order(data: confirmOrderPydantic, _=Depends(get_current_user)):
    try:
        if data.identifier == 'course':
            if await PaymentRecords.exists(order_id=data.order_id, payment_status=1):

                resp = client.payment.fetch(data.payment_id)

                if resp:
                    updated_at = datetime.now(tz)
                    await PaymentRecords.get(order_id=data.order_id).update(
                        payment_id=data.payment_id, payment_status=2, updated_at=updated_at
                    )

                    resp = JSONResponse(
                        {"status": True, "message": "Order confirmed"}, status_code=200)
                else:
                    resp = JSONResponse(
                        {"status": False, "message": "Invalid Payment Id"}, status_code=208)

            else:
                resp = JSONResponse(
                    {"status": False, "message": "Something went wrong"}, status_code=208)

        elif data.identifier == 'material':
            if await StudyMaterialOrderInstance.exists(razorpay_order_id=data.order_id, payment_status=1):
                resp = client.payment.fetch(data.payment_id)
                if resp:
                    updated_at = datetime.now(tz)

                    await StudyMaterialOrderInstance.get(
                        razorpay_order_id=data.order_id
                    ).update(razorpay_payment_id=data.payment_id, updated_at=updated_at)

                    resp = JSONResponse(
                        {"status": True, "message": "Order confirmed"}, status_code=200)
                else:
                    resp = JSONResponse(
                        {"status": False, "message": "Invalid Payment Id"}, status_code=208)

            else:
                resp = JSONResponse(
                    {"status": False, "message": "Something went wrong"}, status_code=208)

        elif data.identifier == 'testseries':
            if await TestSeriesOrders.exists(razorpay_order_id=data.order_id, payment_status=1):
                resp = client.payment.fetch(data.payment_id)
                if resp:
                    updated_at = datetime.now(tz)

                    await TestSeriesOrders.get(
                        razorpay_order_id=data.order_id
                    ).update(razorpay_payment_id=data.payment_id, updated_at=updated_at)

                    resp = JSONResponse(
                        {"status": True, "message": "Order confirmed"}, status_code=200)
                else:
                    resp = JSONResponse(
                        {"status": False, "message": "Invalid Payment Id"}, status_code=208)

            else:
                resp = JSONResponse(
                    {"status": False, "message": "Something went wrong"}, status_code=208)
        else:
            resp = JSONResponse(
                {"status": False, "message": "Something went wrong"}, status_code=208)
        return resp
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208)


async def generate_order_from_webhook(student_id, payment_id, order_id, subscrip_id, bill_amount, source, coupon, coupon_discount, status):
    try:
        updated_at = datetime.now(tz)
        now = datetime.now(tz)

        if await Student.exists(id=student_id):
            user_obj = await Student.get(id=student_id)

            if await CourseSubscriptionPlans.exists(id=subscrip_id):
                subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values("course__id", "validity")
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
                if await StudentChoices.exists(student=user_obj,
                                               course=c_ins, expiry_date__gte=now):

                    subscribed_obj = await StudentChoices.get(student=user_obj,
                                                              course=c_ins, expiry_date__gte=now).values("subscription__id")
                    subscription_id = subscribed_obj['subscription__id']
                    ex_subscript_obj = await CourseSubscriptionPlans.get(id=subscription_id)
                    existing_validity = ex_subscript_obj.validity

                    if existing_validity and (validity > existing_validity):
                        subscribed_plan_obj = await StudentChoices.get(student=user_obj,
                                                                       course=c_ins, expiry_date__gte=now)

                        delta = now - subscribed_plan_obj.created_at
                        used_months = round(delta.days / 30)
                        validity = validity - used_months

                        await StudentChoices.filter(student=user_obj, course=c_ins).update(expiry_date=now)

                if not await StudentChoices.exists(subscription=subs_obj1, student=user_obj, expiry_date__gte=now):

                    # async for team in subs_obj.course:
                    #     if team[0] == 'id':
                    #         cid = team[1]
                    #         break

                    # import pytz
                    # tz = pytz.timezone('Asia/Kolkata')

                    payment_obj = await PaymentRecords.create(
                        student=user_obj,
                        payment_mode=1,
                        subscription=subs_obj1,
                        payment_id=payment_id,
                        order_id=order_id,
                        coupon=coupon,
                        coupon_discount=coupon_discount,
                        bill_amount=bill_amount,
                        gateway_name='Razorpay',
                        payment_status=2,
                        source=source,
                        updated_at=updated_at,
                        created_at=updated_at
                    )
                    datetime_1 = datetime.now(tz)
                    expiry_date = datetime_1 + relativedelta(months=validity)
                    if payment_obj:
                        student_choices_obj = await StudentChoices.create(
                            student=user_obj,
                            course=c_ins,
                            subscription=subs_obj1,
                            payment=payment_obj,
                            subscription_duration=validity,
                            expiry_date=expiry_date,
                            updated_at=updated_at,
                            created_at=updated_at
                        )
                        if student_choices_obj:
                            if await activeSubscription.exists(student=user_obj, course=c_ins):
                                await activeSubscription.filter(
                                    student=user_obj, course=c_ins).delete()
                                await activeSubscription.create(
                                    student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                    course=c_ins, updated_at=datetime_1
                                )
                            else:
                                await activeSubscription.create(
                                    student=user_obj, payment=payment_obj, subscription=subs_obj1,
                                    course=c_ins, updated_at=datetime_1
                                )

                            if status == 'authorized':

                                payment_currency = "INR"
                                resp = client.payment.capture(payment_id, bill_amount, {
                                    "currency": "payment_currency"})

                            fcm_token = user_obj.fcm_token
                            if fcm_token:
                                message_title = 'Payment successful'
                                message_body = "You have successfully purchased the " + \
                                               c_ins.name + " course.\n\nHappy Learning"
                                data_message = {
                                    "open": "profile",
                                    "data_payload": {}
                                }
                                result = push_service.notify_single_device(registration_id=fcm_token,
                                                                           message_title=message_title,
                                                                           message_body=message_body,
                                                                           data_message=data_message)
                            return JSONResponse(
                                {"status": True, "message": "order placed successfully"}, status_code=200)
                        else:

                            return JSONResponse(
                                {"status": False, "message": "Something went wrong"}, status_code=208)

                else:
                    return JSONResponse(
                        {"status": False,
                         "message": "you're already registered with this plan"},
                        status_code=208
                    )

    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208)


@router.post('/webhooks/')
async def webhook(request: Request):
    try:
        data = await request.json()
        print(data)
        # print("============================================")
        payment_id = data['payload']['payment']['entity']['id']
        order_id = data['payload']['payment']['entity']['order_id']
        student_email = data['payload']['payment']['entity']['email']
        payment_amount = data['payload']['payment']['entity']['amount']
        source = data['payload']['payment']['entity']['notes']['source']
        subscription_id = data['payload']['payment']['entity']['notes']['subscription_id']
        order_type = data['payload']['payment']['entity']['notes']['order_type']
        coupon = data['payload']['payment']['entity']['notes']['coupon']
        coupon_discount = data['payload']['payment']['entity']['notes']['coupon_discount']
        student_id = data['payload']['payment']['entity']['notes']['student']
        package_mode = data['payload']['payment']['entity']['notes']['package_mode']

        '''SAVING THE ORDER TO DATABASE GOES HERE'''
        status = data['payload']['payment']['entity']['status']
        if order_type == 'course':
            if not await PaymentRecords.exists(payment_id=payment_id):

                await generate_order_from_webhook(
                    student_id, payment_id, order_id, subscription_id, payment_amount /
                    100, source, coupon, coupon_discount, status
                )
        elif order_type == 'testseries':

            if await Student.exists(id=student_id):
                student = await Student.get(id=student_id)
                ts_instance = await StudyMaterialCourse.get(id=subscription_id)
                if not await TestSeriesOrders.exists(student__id=student_id, test_series_id=subscription_id):
                    updated_at = datetime.now(tz)

                    await TestSeriesOrders.create(student=student, test_series=ts_instance,
                                                  razorpay_payment_id=payment_id, razorpay_order_id=order_id,
                                                  bill_amount=payment_amount / 100, payment_status=2, source=source,
                                                  created_at=updated_at
                                                  )

        elif order_type == 'material':
            student = await Student.get(id=student_id)

            order = await StudyMaterialOrderInstance.create(
                student=student,
                razorpay_payment_id=payment_id,
                razorpay_order_id=order_id,
                bill_amount=payment_amount,
                package_mode=package_mode,

            )
            for item_id in subscription_id:
                item = await StudyMaterialCategories.get(id=item_id)
                await StudyMaterialOrderItems.create(
                    order=order,
                    item_id=item,

                )

        return JSONResponse(
            {"status": True, "message": "Order confirmed"}, status_code=200)
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)})
