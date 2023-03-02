# from datetime import datetime

# import pytz
# from dateutil.relativedelta import relativedelta
# from fastapi import APIRouter, Depends, FastAPI, Form, status, HTTPException
# from fastapi.security import APIKeyCookie
# from fastapi.templating import Jinja2Templates
# from paywix.payu import Payu
# from starlette.config import Config
# from starlette.requests import Request
# from starlette.responses import JSONResponse, RedirectResponse

# from admin_dashboard.models import CourseSubscriptionPlans, Course
# from checkout.models import paymentSession, PaymentRecords
# from student.controller import get_current_user
# from student.models import Student
# from student_choices.models import StudentChoices, activeSubscription

# tz = pytz.timezone('Asia/Kolkata')

# cookie_sec = APIKeyCookie(name="session_id")

# config = Config(".env")
# router = APIRouter()
# app = FastAPI()
# templates = Jinja2Templates(directory="checkout/templates/")

# payu_config = Config(".env")
# merchant_key = payu_config('merchant_key')
# merchant_salt = payu_config('merchant_salt')
# surl = payu_config('success_url')
# furl = payu_config('failure_url')
# mode = payu_config('mode', cast=str)
# payu = Payu(merchant_key, merchant_salt, surl, furl, mode)


# @router.post('/payu_data')
# async def post(request: Request,
#                amount=Form(...),
#                firstname=Form(...),
#                email=Form(...),
#                phone=Form(...),
#                lastname=Form(...),
#                productinfo=Form(...),
#                address1=Form(...),
#                address2=Form(default=None),
#                city=Form(...),
#                state=Form(...),
#                country=Form(...),
#                zipcode=Form(...),
#                txnid=Form(...),
#                _=Depends(get_current_user)):
#     c_subscrip_plan_check = await CourseSubscriptionPlans.exists(id=productinfo)
#     if c_subscrip_plan_check:
#         c_subscrip_plan_instance = await CourseSubscriptionPlans.get(id=productinfo)
#         amount = c_subscrip_plan_instance.plan_price
#     else:
#         raise HTTPException(status_code=208, detail="Something went wrong")
#     payload = {
#         "amount": amount,
#         "firstname": firstname,
#         "email": email,
#         "phone": phone,
#         "lastname": lastname,
#         "productinfo": productinfo,
#         "address1": address1,
#         "address2": address2,
#         "city": city,
#         "state": state,
#         "country": country,
#         "zipcode": zipcode,
#         "txnid": txnid,
#     }
#     payload = payu.transaction(**payload)
#     return templates.TemplateResponse('payu_checkout.html',
#                                       context={'request': request,
#                                                'posted': payload
#                                                })


# # Payu Checkout
# @router.post('/payu_checkout')
# async def payu_checkout(request: Request,
#                         amount=Form(...),
#                         firstname=Form(...),
#                         email=Form(...),
#                         phone=Form(...),
#                         lastname=Form(...),
#                         productinfo=Form(...),
#                         address1=Form(...),
#                         address2=Form(...),
#                         city=Form(...),
#                         state=Form(...),
#                         country=Form(...),
#                         zipcode=Form(...),
#                         txnid=Form(...),
#                         _=Depends(get_current_user)):
#     payload = {
#         "amount": amount,
#         "firstname": firstname,
#         "email": email,
#         "phone": phone,
#         "lastname": lastname,
#         "productinfo": productinfo,
#         "address1": address1,
#         "address2": address2,
#         "city": city,
#         "state": state,
#         "country": country,
#         "zipcode": zipcode,
#         "txnid": txnid,
#     }

#     payu_data = payu.transaction(**payload)
#     return templates.TemplateResponse('payu_checkout.html', context={
#         'request': request,
#         "posted": payu_data,
#     })


# # Payu success return page
# @router.post('/student/payment/success/')
# async def payu_success(request: Request, ):
#     try:
#         updated_at = datetime.now(tz)

#         data = await request.form()
#         # return data
#         response = payu.verify_transaction(data)
#         # return response
#         if response['return_data']['status'] == "success":
#             txnid = response['return_data']['txnid']
#             if await paymentSession.exists(txn_id=txnid):
#                 pay_obj = await paymentSession.get(txn_id=txnid)
#                 # return pay_obj
#                 uid = pay_obj.student
#                 email_obj = await Student.exists(id=uid)
#                 if email_obj:
#                     user_obj = await Student.get(id=uid)
#                     # return user_obj

#                     subscrip_id = response['return_data']['productinfo']
#                     subs_obj = await CourseSubscriptionPlans.get(id=subscrip_id).values("course__id", "validity")
#                     subs_obj1 = await CourseSubscriptionPlans.get(id=subscrip_id)
#                     # return subs_obj

#                     cid = subs_obj[0]["course__id"]
#                     validity = subs_obj[0]["validity"]
#                     #     # async for team in subs_obj.course:
#                     #     #     if team[0] == 'id':
#                     #     #         cid = team[1]
#                     #     #         break
#                     c_ins = await Course.get(id=cid)
#                     if not await PaymentRecords.exists(subscription=subs_obj1, student=user_obj):

#                         payment_obj = await PaymentRecords.create(
#                             student=user_obj,
#                             subscription=subs_obj1,
#                             payment_id=response['return_data']['payuMoneyId'],
#                             gateway_name="Payu"
#                         )
#                         datetime_1 = datetime.now(tz)

#                         expiry_date = datetime_1 + \
#                             relativedelta(months=validity)
#                         if payment_obj:
#                             await StudentChoices.create(
#                                 student=user_obj,
#                                 course=c_ins,
#                                 subscription=subs_obj1,
#                                 payment=payment_obj,
#                                 subscription_duration=validity,
#                                 expiry_date=expiry_date
#                             )

#                             if await activeSubscription.exists(student=user_obj, course=c_ins):
#                                 activePlan_instance = await activeSubscription.get(
#                                     student=user_obj, course=c_ins
#                                 )
#                                 activePlan_instance.subscription = subs_obj
#                                 await activePlan_instance.save()
#                             else:
#                                 await activeSubscription.create(
#                                     student=user_obj, subscription=subs_obj1,
#                                     course=c_ins, payment=payment_obj, updated_at=datetime_1
#                                 )

#                             await pay_obj.delete()
#                             # print(response)
#                             print(response['return_data']['status'])
#                             print("PaymentId: ")
#                             print(response['return_data']['payuMoneyId'])
#                             print(response['return_data']['mode'])
#                             print(response['return_data']['mihpayid'])
#                             print(response['return_data']['net_amount_debit'])
#                             print(
#                                 '========================user here========================')
#                             # return {"stop here"}
#                             return RedirectResponse(
#                                 url='/student/new-dashboard/',
#                                 status_code=status.HTTP_303_SEE_OTHER)
#                         else:
#                             return {"Order error"}
#                     else:
#                         return JSONResponse(
#                             {"status": False,
#                                 "message": "you're already registered with this plan"},
#                             status_code=208
#                         )
#                 else:
#                     return {"Student Id does not exist"}

#             else:
#                 return {"Transaction Id error"}
#         else:
#             return {"Payment error"}
#     except Exception as ex:
#         raise HTTPException(status_code=208, detail=str(ex))


# # Payu failure page
# @router.post('/student/payment/failure/')
# async def payu_failure(request: Request, ):
#     # print(request)
#     # response = payu.verify_transaction(payload)

#     return JSONResponse()
