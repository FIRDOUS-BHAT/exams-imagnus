from fastapi import APIRouter
from screen_banners import route as bannerRoute
from student.apis import route as studentRoute
from admin_dashboard.apis import route as preferenceRoute
from send_sms import api
from checkout.apis import route as checkoutRoute
from study_material.apis import route as studyMaterialRoute
from FCM import route as FcmRoute


api_router = APIRouter()
# api_router.include_router(FcmRoute, prefix='/notify')
api_router.include_router(bannerRoute.router, )
api_router.include_router(studentRoute.router, prefix='/student')
api_router.include_router(preferenceRoute.router, prefix='/student')
api_router.include_router(api.router, )
api_router.include_router(checkoutRoute.router, )
api_router.include_router(studyMaterialRoute.router,)
