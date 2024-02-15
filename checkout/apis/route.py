from tortoise.exceptions import DoesNotExist
import logging
from collections import namedtuple
from functools import lru_cache
import json
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
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, validator
from starlette.responses import JSONResponse
from FCM.route import push_service
from admin_dashboard.models import Coupons, CourseSubscriptionPlans, Course
from checkout.models import (
    MobileCart,
    PaymentRecordsIn_Pydantic,
    PaymentRecords,
    PaymentRecords_Pydantic,
)
from configs import appinfo
from student.apis.pydantic_models import SubscriptionPlanPydantic
from student.models import Student
from student_choices.models import StudentChoices, activeSubscription
from study_material.models import (
    StudyMaterialCategories,
    StudyMaterialCourse,
    StudyMaterialOrderInstance,
    StudyMaterialOrderItems,
    TestSeriesOrders,
)
from utils.util import get_current_user

router = APIRouter()

tz = pytz.timezone("Asia/Kolkata")
updated_at = datetime.now(tz)


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()
razorpay_key = settings.razorpay_key
razorpay_secret = settings.razorpay_secret
app_url = settings.app_url
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


@router.post(
    "/place_manual_order",
)
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
                    subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values(
                        "course__id", "validity"
                    )
                    subs_obj1 = await CourseSubscriptionPlans.get(id=subscrip_id)

                    if not await PaymentRecords.exists(
                        subscription=subs_obj1, student=user_obj
                    ):
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
                            gateway_name="Razorpay",
                            updated_at=updated_at,
                            created_at=updated_at,
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
                                        updated_at=datetime_1,
                                    )
                                else:
                                    await activeSubscription.create(
                                        student=user_obj,
                                        payment=payment_obj,
                                        subscription=subs_obj1,
                                        course=c_ins,
                                        updated_at=datetime_1,
                                    )

                                fcm_token = user_obj.fcm_token
                                if fcm_token:
                                    message_title = "Payment successful"
                                    message_body = (
                                        "You have successfully purchased the "
                                        + c_ins.name
                                        + " course.\n\nHappy Learning"
                                    )
                                    data_message = {
                                        "open": "dashboard",
                                        "data_payload": {},
                                    }
                                    result = push_service.notify_single_device(
                                        registration_id=fcm_token,
                                        message_title=message_title,
                                        click_action="FLUTTER_NOTIFICATION_CLICK",
                                        message_body=message_body,
                                        data_message=data_message,
                                    )
                                response.append(
                                    JSONResponse(
                                        {
                                            "status": True,
                                            "message": "order placed successfully for mobile number "
                                            + uid,
                                        },
                                        status_code=200,
                                    )
                                )
                            else:

                                response.append(
                                    JSONResponse(
                                        {
                                            "status": False,
                                            "message": "Something went wrong with mobile number "
                                            + uid,
                                        },
                                        status_code=208,
                                    )
                                )

                    else:
                        error_response.append(
                            JSONResponse(
                                {
                                    "status": False,
                                    "message": "This mobile number "
                                    + uid
                                    + " is already registered with this plan",
                                },
                                status_code=208,
                            )
                        )

            else:
                error_response.append(
                    JSONResponse(
                        {"error": "This mobile number " + uid + " is not registered"},
                        status_code=208,
                    )
                )
        return {"success": response, "error": error_response}
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


# Define the namedtuple for order parameters
OrderParams = namedtuple(
    "OrderParams",
    [
        "payment_mode",
        "payment_status",
        "payment_id",
        "order_id",
        "gateway_name",
        "coupon",
        "coupon_discount",
        "notes",
        "source",
        "bill_amount",
        "student_id",
        "subscription_id",
    ],
)


async def create_order(data):
    try:
        now = datetime.now(tz)

        uid = data.student_id
        payment_id = data.payment_id
        payment_status = 1
        payment_mode = 1
        gateway_name = "Razorpay"
        razorpay_resp = None
        order_id = None
        bill_amount = data.bill_amount
        if payment_id and data.source != "adm":
            razorpay_resp = client.payment.fetch(data.payment_id)

            # pretty_print = json.dumps(razorpay_resp, indent=4)

            if razorpay_resp["status"] == "authorized":
                payment_status = 2
                order_id = razorpay_resp["order_id"]
                bill_amount = razorpay_resp["amount"] / 100

            if razorpay_resp and (
                not await PaymentRecords.exists(payment_id=payment_id)
            ):
                payment_status = 2
            else:
                return JSONResponse(
                    {"status": False, "message": "Invalid Payment Id"},
                    status_code=208,
                )

        if await Student.exists(id=uid):
            subscrip_id = data.subscription_id

            user_obj = await Student.get(id=uid)

            if await CourseSubscriptionPlans.exists(id=subscrip_id):
                subs_obj1 = await CourseSubscriptionPlans.get(id=subscrip_id)
                cid = subs_obj1.course_id
                validity = subs_obj1.validity
                plan_price = subs_obj1.plan_price
                if razorpay_resp:
                    print("Yes in razorpay_resp")
                    print("data.coupon", data.coupon)
                    if not data.coupon:

                        if round(plan_price) != round(razorpay_resp["amount"] / 100):
                            return JSONResponse(
                                {
                                    "status": False,
                                    "message": "Invalid bill amount for the plan",
                                },
                                status_code=208,
                            )

                    else:
                        # Check if the coupon is valid and subtract the discount from the plan_price then compare with the razorpay amount
                        if await Coupons.exists(
                            name=data.coupon, subscription_id=subscrip_id
                        ):
                            coupon_obj = await Coupons.get(name=data.coupon)
                            if coupon_obj.coupon_type == 1:
                                discount = (plan_price * coupon_obj.discount) / 100
                            elif coupon_obj.coupon_type == 2:
                                discount = coupon_obj.discount
                            plan_price = plan_price - discount

                            if round(plan_price) != round(
                                razorpay_resp["amount"] / 100
                            ):
                                return JSONResponse(
                                    {
                                        "status": False,
                                        "message": "Invalid bill amount for the plan",
                                    },
                                    status_code=208,
                                )
                        else:
                            return JSONResponse(
                                {"status": False, "message": "Invalid Coupon"},
                                status_code=208,
                            )

                c_ins = await Course.get(id=cid)

                """check if any subscription"""
                existing_validity = 0
                used_months = 0
                if await StudentChoices.exists(
                    student=user_obj,
                    course=c_ins,
                    expiry_date__gte=now,
                    payment__payment_status=2,
                ):

                    subscribed_obj = await StudentChoices.get(
                        student=user_obj,
                        course=c_ins,
                        expiry_date__gte=now,
                        payment__payment_status=2,
                    ).values("subscription__id")
                    subscription_id = subscribed_obj["subscription__id"]
                    ex_subscript_obj = await CourseSubscriptionPlans.get(
                        id=subscription_id
                    )
                    existing_validity = ex_subscript_obj.validity

                    if existing_validity and (validity > existing_validity):
                        subscribed_plan_obj = await StudentChoices.get(
                            student=user_obj,
                            course=c_ins,
                            expiry_date__gte=now,
                            payment__payment_status=2,
                        )

                        delta = now - subscribed_plan_obj.created_at
                        used_months = round(delta.days / 30)
                        validity = validity - used_months

                        await StudentChoices.filter(
                            student=user_obj, course=c_ins
                        ).update(expiry_date=now)

                if not await StudentChoices.exists(
                    subscription__id=subscrip_id,
                    student=user_obj,
                    expiry_date__gte=now,
                    payment__payment_status=2,
                ):
                    if data.source == "adm":
                        payment_status = 2
                        payment_mode = 2
                        gateway_name = "Manual"

                    payment_obj = await PaymentRecords.create(
                        student=user_obj,
                        payment_mode=payment_mode,
                        subscription=subs_obj1,
                        payment_id=payment_id,
                        order_id=order_id,
                        coupon=data.coupon,
                        coupon_discount=data.coupon_discount,
                        bill_amount=bill_amount,
                        gateway_name=gateway_name,
                        payment_status=payment_status,
                        updated_at=updated_at,
                        created_at=updated_at,
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
                                    updated_at=datetime_1,
                                )
                            else:
                                await activeSubscription.create(
                                    student=user_obj,
                                    payment=payment_obj,
                                    subscription=subs_obj1,
                                    course=c_ins,
                                    updated_at=datetime_1,
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
                            # Remove the unused import statement
                            # from send_mails.controller import send_email_backgroundtasks

                            email_body = {
                                "name": user_obj.fullname,
                                "course": c_ins.name,
                                "payment_id": payment_id,
                                "order_id": data.order_id,
                                "total_amount": data.bill_amount,
                            }

                            # async with httpx.AsyncClient() as client:
                            #     await client.post(app_url+'/send-email/backgroundtasks?email_to='+user_obj.email,
                            #                       json=jsonable_encoder(email_body))

                            # Check if the provided subscription_id is in the list of special IDs

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


# List of special subscription IDs
SPECIAL_SUBSCRIPTION_IDS = ["ce9d35e6-08b2-4535-8c95-daf9ee056e98"]


logger = logging.getLogger(__name__)


async def place_free_subscription(str_subscription_id, student_id):
    """Check if the provided subscription_id is in the list of special IDs"""

    try:
        print("Subscription ID:", repr(str_subscription_id))
        print("Special IDs:", SPECIAL_SUBSCRIPTION_IDS)

        # Strip any leading/trailing whitespace
        str_subscription_id = str(str_subscription_id)

        if str_subscription_id in SPECIAL_SUBSCRIPTION_IDS:

            # If it is, set the order parameters to the provided values

            order_params = OrderParams(
                payment_mode=1,
                payment_status=1,
                payment_id="",
                order_id="",
                gateway_name="",
                coupon="",
                coupon_discount=0,
                notes="Free offer",
                source="adm",
                bill_amount=0,
                student_id=student_id,  # Assuming student_id is also passed in the request
                subscription_id="ea9c70f3-cbd5-43c7-9d39-f2721941f8c3",
            )

            print("Order parameters set to: ", order_params)

            # Call the place_order function with the set parameters
            await place_order(order_params)

            print("Free Order placed successfully.")

            return True
        print("Special subscription ID not matched.")
        return False
    except Exception as ex:
        print("Error while placing free order: ", str(ex))
        return False


class OrderPlacePydantic(BaseModel):
    payment_id: str
    order_id: str
    coupon: str
    coupon_discount: int
    notes: str
    source: str
    bill_amount: int
    student_id: str
    subscription_id: str


@router.post(
    "/place_order",
)
async def place_order(data: OrderPlacePydantic, _=Depends(get_current_user)):
    # Check and process the regular order
    try:
        result_response = await create_order(data)

        # Extract and decode the body from the JSONResponse
        result_content = result_response.body.decode("utf-8")
        # Convert string content to dictionary for processing
        result_dict = json.loads(result_content)

        if result_dict.get("status"):
            str_subscription_id = str(data.subscription_id).lower()

            await place_free_subscription(str_subscription_id, data.student_id)

        return result_response

    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


# return await PaymentRecords_Pydantic.from_tortoise_orm()


async def place_target_batch_orders(data):
    # try:
    updated_at = datetime.now(tz)
    now = datetime.now(tz)

    uid = data["student_id"]

    if await Student.exists(id=uid):
        user_obj = await Student.get(id=uid)
        subscrip_id = data["subscription_id"]
        payment_id = data["payment_id"]

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
            if await StudentChoices.exists(
                student=user_obj,
                course=c_ins,
                expiry_date__gte=now,
                payment__payment_status=2,
            ):

                subscribed_obj = await StudentChoices.get(
                    student=user_obj,
                    course=c_ins,
                    expiry_date__gte=now,
                    payment__payment_status=2,
                ).values("subscription__id")
                subscription_id = subscribed_obj["subscription__id"]
                ex_subscript_obj = await CourseSubscriptionPlans.get(id=subscription_id)
                existing_validity = ex_subscript_obj.validity

                if existing_validity and (validity > existing_validity):
                    subscribed_plan_obj = await StudentChoices.get(
                        student=user_obj,
                        course=c_ins,
                        expiry_date__gte=now,
                        payment__payment_status=2,
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

                    await StudentChoices.filter(student=user_obj, course=c_ins).update(
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
                course=c_ins,
                student=user_obj,
                expiry_date__gte=now,
                payment__payment_status=2,
            ):

                gateway_name = data["gateway_name"]

                # async for team in subs_obj.course:
                #     if team[0] == 'id':
                #         cid = team[1]
                #         break

                # import pytz
                # tz = pytz.timezone('Asia/Kolkata')

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
                            {"status": True, "message": "order placed successfully"},
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


@router.get("/activeSubscriptions/{student_id}/{subscription_id}/")
async def active_subscription(
    student_id: str, subscription_id: str, _=Depends(get_current_user)
):
    resp = await activeSubscription.filter(student=student_id)
    return resp


@router.get("/get_all_payment_records")
async def all_payment_records(_=Depends(get_current_user)):
    obj = await PaymentRecords.all()
    return obj


@router.get("/get_all_student_choices")
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
    created_at: Optional[datetime]

    @validator("created_at", pre=True, always=True)
    def set_ts_now(cls, v):
        return v or datetime.now()


@router.post("/get_student_order_payment/", response_model=List[OrderHistoryPydantic])
async def get_order_history(data: PaymentHistoryPydantic, _=Depends(get_current_user)):
    try:
        uid = data.uid
        if await Student.exists(id=uid):
            student_instance = await Student.get(id=uid)
            if await PaymentRecords.exists(student=student_instance):
                resp = await PaymentRecords_Pydantic.from_queryset(
                    PaymentRecords.filter(student=student_instance)
                )
                return resp
            else:
                return []
        else:
            return []
    except Exception as ex:

        return []


@router.post("/add_pre_target_batch_to_mains_students")
async def add_pre_target_batch_to_mains_students(_=Depends(get_current_user)):
    try:
        resp = []
        main_obj = await PaymentRecords.filter(
            subscription__id__in=[
                "23438cf5-c964-425a-bf9d-82ee3a280e3e",
                "02177d58-6053-401b-bf9d-69b81f2ca510",
            ]
        )
        i = 0
        for order in main_obj:

            if await PaymentRecords.exists(
                student__id=order.student_id,
                subscription__id="baa368fb-388a-4e55-b52b-ae4fa70817c1",
            ):
                # print(order.student_id)

                var = await PaymentRecords.filter(
                    student__id=order.student_id,
                    subscription__id="baa368fb-388a-4e55-b52b-ae4fa70817c1",
                ).update(bill_amount="10")

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
                res = {i + ".updated"}
                resp.append(res)
            return resp

    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


class confirmOrderPydantic(BaseModel):
    identifier: str
    order_id: str
    payment_id: str
    signature: Optional[str] = None


@router.post("/confirm_order")
async def confirm_order(data: confirmOrderPydantic, _=Depends(get_current_user)):
    try:
        if data.identifier == "course":
            if await PaymentRecords.exists(order_id=data.order_id, payment_status=1):

                resp = client.payment.fetch(data.payment_id)

                if resp:
                    updated_at = datetime.now(tz)
                    await PaymentRecords.get(order_id=data.order_id).update(
                        payment_id=data.payment_id,
                        payment_status=2,
                        updated_at=updated_at,
                    )

                    resp = JSONResponse(
                        {"status": True, "message": "Order confirmed"}, status_code=200
                    )
                else:
                    resp = JSONResponse(
                        {"status": False, "message": "Invalid Payment Id"},
                        status_code=208,
                    )

            else:
                resp = JSONResponse(
                    {"status": False, "message": "Something went wrong"},
                    status_code=208,
                )

        elif data.identifier == "material":
            if await StudyMaterialOrderInstance.exists(
                razorpay_order_id=data.order_id, payment_status=1
            ):
                resp = client.payment.fetch(data.payment_id)
                if resp:
                    updated_at = datetime.now(tz)

                    await StudyMaterialOrderInstance.get(
                        razorpay_order_id=data.order_id
                    ).update(razorpay_payment_id=data.payment_id, updated_at=updated_at)

                    resp = JSONResponse(
                        {"status": True, "message": "Order confirmed"}, status_code=200
                    )
                else:
                    resp = JSONResponse(
                        {"status": False, "message": "Invalid Payment Id"},
                        status_code=208,
                    )

            else:
                resp = JSONResponse(
                    {"status": False, "message": "Something went wrong"},
                    status_code=208,
                )

        elif data.identifier == "testseries":
            if await TestSeriesOrders.exists(
                razorpay_order_id=data.order_id, payment_status=1
            ):
                resp = client.payment.fetch(data.payment_id)
                if resp:
                    updated_at = datetime.now(tz)

                    await TestSeriesOrders.get(razorpay_order_id=data.order_id).update(
                        razorpay_payment_id=data.payment_id, updated_at=updated_at
                    )

                    resp = JSONResponse(
                        {"status": True, "message": "Order confirmed"}, status_code=200
                    )
                else:
                    resp = JSONResponse(
                        {"status": False, "message": "Invalid Payment Id"},
                        status_code=208,
                    )

            else:
                resp = JSONResponse(
                    {"status": False, "message": "Something went wrong"},
                    status_code=208,
                )
        else:
            resp = JSONResponse(
                {"status": False, "message": "Something went wrong"}, status_code=208
            )
        return resp
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


async def generate_order_from_webhook(
    student_id,
    payment_id,
    order_id,
    subscrip_id,
    bill_amount,
    source,
    coupon,
    coupon_discount,
    status,
):
    try:
        updated_at = datetime.now(tz)
        now = datetime.now(tz)

        if await Student.exists(id=student_id):
            user_obj = await Student.get(id=student_id)

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
                if await StudentChoices.exists(
                    student=user_obj,
                    course=c_ins,
                    expiry_date__gte=now,
                    payment__payment_status=2,
                ):

                    subscribed_obj = await StudentChoices.get(
                        student=user_obj,
                        course=c_ins,
                        expiry_date__gte=now,
                        payment__payment_status=2,
                    ).values("subscription__id")
                    subscription_id = subscribed_obj["subscription__id"]
                    ex_subscript_obj = await CourseSubscriptionPlans.get(
                        id=subscription_id
                    )
                    existing_validity = ex_subscript_obj.validity

                    if existing_validity and (validity > existing_validity):
                        subscribed_plan_obj = await StudentChoices.get(
                            student=user_obj,
                            course=c_ins,
                            expiry_date__gte=now,
                            payment__payment_status=2,
                        )

                        delta = now - subscribed_plan_obj.created_at
                        used_months = round(delta.days / 30)
                        validity = validity - used_months

                        await StudentChoices.filter(
                            student=user_obj, course=c_ins
                        ).update(expiry_date=now)

                if not await StudentChoices.exists(
                    subscription=subs_obj1,
                    student=user_obj,
                    expiry_date__gte=now,
                    payment__payment_status=2,
                ):

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
                        gateway_name="Razorpay",
                        payment_status=2,
                        source=source,
                        updated_at=updated_at,
                        created_at=updated_at,
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
                                    updated_at=datetime_1,
                                )
                            else:
                                await activeSubscription.create(
                                    student=user_obj,
                                    payment=payment_obj,
                                    subscription=subs_obj1,
                                    course=c_ins,
                                    updated_at=datetime_1,
                                )

                            if status == "authorized":

                                payment_currency = "INR"
                                resp = client.payment.capture(
                                    payment_id,
                                    bill_amount,
                                    {"currency": "payment_currency"},
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


@router.post("/webhooks/")
async def webhook(request: Request):
    try:
        c_ins = None
        data = await request.json()

        # print("============================================")
        payment_id = data["payload"]["payment"]["entity"]["id"]
        order_id = data["payload"]["payment"]["entity"]["order_id"]
        payment_amount = data["payload"]["payment"]["entity"]["amount"]

        """Temporary Use Web only"""
        if data["payload"]["payment"]["entity"]["notes"]["source"]:
            source = data["payload"]["payment"]["entity"]["notes"]["source"]
            if source == "web" or source == "app":
                subscription_id = data["payload"]["payment"]["entity"]["notes"][
                    "subscription_id"
                ]
                order_type = data["payload"]["payment"]["entity"]["notes"]["order_type"]
                coupon = data["payload"]["payment"]["entity"]["notes"]["coupon"]
                coupon_discount = data["payload"]["payment"]["entity"]["notes"][
                    "coupon_discount"
                ]
                student_id = data["payload"]["payment"]["entity"]["notes"]["student"]
                package_mode = data["payload"]["payment"]["entity"]["notes"][
                    "package_mode"
                ]
                student = await Student.get(id=student_id)

                """SAVING THE ORDER TO DATABASE GOES HERE"""
                status = data["payload"]["payment"]["entity"]["status"]
                if order_type == "course":
                    subs_ins = await CourseSubscriptionPlans.get(
                        id=subscription_id
                    ).values("course__name")
                    c_ins = subs_ins["course__name"]
                    if not await PaymentRecords.exists(payment_id=payment_id):

                        await generate_order_from_webhook(
                            student_id,
                            payment_id,
                            order_id,
                            subscription_id,
                            payment_amount / 100,
                            source,
                            coupon,
                            coupon_discount,
                            status,
                        )
                elif order_type == "testseries":

                    if await Student.exists(id=student_id):

                        ts_instance = await StudyMaterialCourse.get(id=subscription_id)
                        subs_ins = await StudyMaterialCourse.get(
                            id=subscription_id
                        ).values("course__name")
                        c_ins = subs_ins["course__name"]
                        if not await TestSeriesOrders.exists(
                            student__id=student_id, test_series_id=subscription_id
                        ):
                            updated_at = datetime.now(tz)

                            await TestSeriesOrders.create(
                                student=student,
                                test_series=ts_instance,
                                razorpay_payment_id=payment_id,
                                razorpay_order_id=order_id,
                                bill_amount=payment_amount / 100,
                                payment_status=2,
                                source=source,
                                created_at=updated_at,
                            )

                elif order_type == "material":

                    order = await StudyMaterialOrderInstance.create(
                        student=student,
                        razorpay_payment_id=payment_id,
                        razorpay_order_id=order_id,
                        bill_amount=payment_amount / 100,
                        package_mode=int(package_mode),
                    )
                    import ast

                    if source == "app":
                        if await MobileCart.exists(order_id=order_id):

                            cart_data = await MobileCart.get(
                                student__id=student_id, order_id=order_id
                            )

                            item_list = ast.literal_eval(cart_data.subscription_ids)
                        else:
                            return JSONResponse(
                                {"status": False, "message": "order id invalid"}
                            )

                    else:
                        item_list = ast.literal_eval(subscription_id)
                    for item_id in item_list:

                        item = await StudyMaterialCategories.get(id=item_id)
                        subs_ins = await StudyMaterialCategories.get(id=item_id).values(
                            "course__course__name"
                        )
                        c_ins = subs_ins["course__course__name"]
                        updated_at = datetime.now(tz)

                        await StudyMaterialOrderItems.create(
                            order=order, item_id=item, created_at=updated_at
                        )
                        await MobileCart.get(order_id=order_id).delete()

                email_body = {
                    "name": student.fullname,
                    "course": c_ins,
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "total_amount": payment_amount / 100,
                }

                async with httpx.AsyncClient() as client:
                    await client.post(
                        app_url
                        + "/send-email/backgroundtasks?email_to="
                        + student.email,
                        json=jsonable_encoder(email_body),
                    )
                return JSONResponse(
                    {"status": True, "message": "Order confirmed"}, status_code=200
                )

        else:
            return JSONResponse(
                {"status": False, "message": "Request incomplete"}, status_code=200
            )
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)})


class CartParams(BaseModel):
    student_id: uuid.UUID
    order_id: str
    order_type: int
    cart_ids: str


@router.post("/mobile_cart/")
async def mobile_cart(data: CartParams, _=Depends(get_current_user)):
    if await Student.exists(id=data.student_id):
        student = await Student.get(id=data.student_id)
        if not await MobileCart.exists(order_id=data.order_id):
            await MobileCart.get(order_id=data.order_id).delete()
            await MobileCart.create(
                student=student,
                order_id=data.order_id,
                order_type=data.order_type,
                subscription_ids=data.cart_ids,
            )
    else:
        return JSONResponse(
            {"status": False, "message": "operation not permitted"}, status_code=422
        )

    return JSONResponse({"status": True, "message": "Cart loaded"}, status_code=200)


"""New code to grant access to warrior batchs"""


@router.post("/grant_access_to_warriors_batch")
async def grant_access_to_warriors_batch_api(_=Depends(get_current_user)):
    await grant_access_to_warriors_batch(
        source_batch_ids=[
            "80265e0a-908e-4aae-b960-4b9f0839da73",
            "2adbab33-5634-4370-af90-0234b44156a0",
        ],
        target_batch_id="dbab4049-f96b-41e5-bc6c-8ef5e449ffad",
    )


async def grant_access_to_warriors_batch(source_batch_ids: list, target_batch_id: str):
    """
    Grant access to the 'Warriors batch' for students from the specified source batches.
    """
    expiry_date = datetime(2024, 3, 20)
    target_batch = await get_subscription_plan(target_batch_id)

    for source_batch_id in source_batch_ids:
        source_batch = await get_subscription_plan(source_batch_id)
        if source_batch:
            await process_students_from_source_batch(
                source_batch, target_batch, expiry_date
            )


from tortoise.query_utils import Prefetch


async def get_subscription_plan(batch_id: str):
    """
    Fetch a subscription plan based on batch ID.
    """
    try:
        subscription_plan = await CourseSubscriptionPlans.get(
            id=batch_id
        ).prefetch_related(Prefetch("course", queryset=Course.all()))
        return subscription_plan
    except DoesNotExist:
        print(f"Batch with ID {batch_id} not found.")
        return None


async def process_students_from_source_batch(source_batch, target_batch, expiry_date):
    """
    Process each student from the source batch to grant access to the target batch.
    """
    current_subscriptions = await StudentChoices.filter(
        subscription=source_batch, expiry_date__gte=datetime.now(tz)
    ).prefetch_related("student")

    for subscription in current_subscriptions:
        student = subscription.student
        if not await has_existing_access(student, target_batch):
            payment_record = await create_payment_record(student, target_batch)
            if payment_record:
                await create_student_choice(
                    student, target_batch, expiry_date, payment_record
                )
                await update_or_create_active_subscription(
                    student, target_batch, payment_record
                )
                print(
                    f"Granted access to Student ID: {student.id} for Warriors batch until {expiry_date.strftime('%Y-%m-%d')}"
                )


async def has_existing_access(student, target_batch):
    """
    Check if the student already has access to the target batch.
    """
    return await StudentChoices.filter(
        student=student, subscription=target_batch
    ).exists()


async def create_payment_record(student, subscription_plan):
    """
    Create a PaymentRecords entry for a student for the specified subscription plan.
    """
    try:

        return await PaymentRecords.create(
            student=student,
            payment_mode=2,
            payment_status=2,
            subscription=subscription_plan,
            bill_amount=0,
            gateway_name="Admin",
            notes="Access to Warriors for those who have Shaurya 3.0",
            source="adm",
            updated_at=datetime.now(tz),
            created_at=datetime.now(tz),
        )
    except Exception as ex:
        print(f"Error while creating PaymentRecords: {str(ex)}")


async def create_student_choice(
    student, subscription_plan, expiry_date, payment_record
):
    """
    Create a StudentChoices record to link the student with the new batch access.
    """
    try:

        print(f"Creating StudentChoices for Student course: {subscription_plan.course}")

        print(f"Student: {student}, Type: {type(student)}")
        print(
            f"Course: {subscription_plan.course}, Type: {type(subscription_plan.course)}"
        )
        print(
            f"Subscription Plan: {subscription_plan}, Type: {type(subscription_plan)}"
        )
        print(f"Payment Record: {payment_record}, Type: {type(payment_record)}")

        return await StudentChoices.create(
            student=student,
            course=subscription_plan.course,
            subscription=subscription_plan,
            expiry_date=expiry_date,
            payment=payment_record,
            subscription_duration=subscription_plan.validity,
        )

    except Exception as ex:
        print(f"Error while creating StudentChoices: {str(ex)}")


async def update_or_create_active_subscription(
    student, subscription_plan, payment_record
):
    """
    Update or create an activeSubscription record for the student for the target batch.
    """
    await activeSubscription.create(
        student=student,
        subscription=subscription_plan,
        course=subscription_plan.course,
        payment=payment_record,
    )
    print(
        f"Created new activeSubscription record for Student ID: {student.id} for Warriors batch."
    )


# delete duplicate subscription of warrior batch for a student
@router.post("/delete_duplicate_warriors_subscription")
async def delete_duplicate_warriors_subscription_api(_=Depends(get_current_user)):
    await delete_duplicate_warriors_subscription()


async def delete_duplicate_warriors_subscription():
    """
    Delete duplicate subscriptions of the 'Warriors batch' for students.
    """
    target_batch_id = "dbab4049-f96b-41e5-bc6c-8ef5e449ffad"
    target_batch = await get_subscription_plan(target_batch_id)

    if target_batch:
        await process_students_for_duplicate_subscriptions(target_batch)
    else:
        print(f"Warriors batch with ID {target_batch_id} not found.")


async def process_students_for_duplicate_subscriptions(target_batch):
    """
    Process each student to delete duplicate subscriptions of the target batch.
    """
    current_subscriptions = (
        await StudentChoices.filter(
            subscription=target_batch, expiry_date__gte=datetime.now(tz)
        )
        .prefetch_related("student")
        .order_by("-created_at")
    )

    for subscription in current_subscriptions:
        student = subscription.student
        if await has_duplicate_subscriptions(student, target_batch):
            await delete_duplicate_subscriptions(student, target_batch)
            print(
                f"Deleted duplicate subscriptions for Student ID: {student.id} for Warriors batch."
            )


async def has_duplicate_subscriptions(student, target_batch):
    """
    Check if the student has duplicate subscriptions of the target batch.
    """
    return (
        await StudentChoices.filter(
            student=student,
            subscription=target_batch,
            expiry_date__gte=datetime.now(tz),
        ).count()
        > 1
    )


async def delete_duplicate_subscriptions(student, target_batch):
    """
    Delete duplicate subscriptions of the target batch for the student.
    """
    await StudentChoices.filter(student=student, subscription=target_batch).order_by(
        "-created_at"
    ).offset(1).delete()
    # delete from active subscription model as well
    await activeSubscription.filter(
        student=student, subscription=target_batch
    ).order_by("-created_at").offset(1).delete()
    # delete from payment record model as well
    await PaymentRecords.filter(student=student, subscription=target_batch).order_by(
        "-created_at"
    ).offset(1).delete()
    print(
        f"Deleted duplicate subscriptions for Student ID: {student.id} for Warriors batch."
    )
