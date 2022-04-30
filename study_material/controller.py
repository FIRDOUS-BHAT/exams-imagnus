import uuid
import os
from functools import lru_cache
from typing import Optional
import json
from botocore.client import BaseClient
from fastapi import APIRouter, FastAPI, Form, UploadFile, File, Depends, status, HTTPException
from fastapi.encoders import jsonable_encoder
import pandas as pd
from pydantic.main import BaseModel
from slugify import slugify
from starlette.requests import Request
from starlette.responses import RedirectResponse, JSONResponse
from starlette.templating import Jinja2Templates
import razorpay
from admin_dashboard.controller import upload_images, upload_pdf_notes
from admin_dashboard.models import Course_Pydantic, Course
from aws_services.deps import s3_auth
from configs import appinfo
from student.controller import get_current_user
from student.models import Student
from study_material.models import StudyMaterialName, StudyMaterialName_Pydantic, StudyMaterialCourse, \
    StudyMaterialCourse_Pydantic, StudyMaterialCategories, StudyMaterialCategories_Pydantic, StudyMaterialOrderInstance, \
    StudyMaterialCartInstance, StudyMaterialOrderItems, StudyMaterialTestSeries, StudyMaterialTestSeries_Pydantic, StudyMaterialTestSeriesQuestions, TestSeriesOrders
import pytz
from datetime import datetime


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()
razorpay_key = settings.razorpay_key
razorpay_secret = settings.razorpay_secret
app_name = settings.app_name
app_version = settings.app_version
app_url = settings.app_url

client = razorpay.Client(auth=(razorpay_key, razorpay_secret))
client.set_app_details({"title": app_name, "version": app_version})

tz = pytz.timezone('Asia/Kolkata')

router = APIRouter()

app = FastAPI(debug=True)
backend_templates = Jinja2Templates(
    directory="study_material/templates/backend")
frontend_templates = Jinja2Templates(
    directory="study_material/templates/frontend")


# '''
# Backend controller
# '''


@router.get('/admin/add_study_material/')
async def add_study_material(request: Request):
    try:
        material_obj = await StudyMaterialName.all()
        course_obj = await Course.all()
        first_study_material_name = await StudyMaterialName.first()
        category_course_obj = await StudyMaterialCourse.all().values(
            "id","course__name","web_icon","bundle_price","bundle_dsc_price","material__name"
            )
        
        
        # each_category_course_obj = await StudyMaterialCourse_Pydantic.from_queryset(
        #     StudyMaterialCourse.filter(
        #         material__id=first_study_material_name.id)
        # )

        return backend_templates.TemplateResponse('study_material.html', context={
            'request': request,
            'study_material_names': material_obj,
            'courses': course_obj,
            'category_course': category_course_obj,
            # 'each_category_courses': each_category_course_obj,
            'add_study_material_active': 'active',

        })
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/admin/study_material_notes/')
async def add_study_material(request: Request):
    try:
        study_material_categories_obj = await StudyMaterialCategories_Pydantic.from_queryset(
            StudyMaterialCategories.filter(is_active=True)
        )

        return backend_templates.TemplateResponse('study_material_notes.html', context={
            'request': request,
            'study_material_categories_obj': study_material_categories_obj,
            'add_study_material_active': 'active',

        })
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/admin/study_material_test_series/')
async def add_study_material(request: Request):
    try:
        testseries_obj = await StudyMaterialTestSeries_Pydantic.from_queryset(
            StudyMaterialTestSeries.all()
        )

        return backend_templates.TemplateResponse('study_material_testseries.html', context={
            'request': request,

            'add_study_material_active': 'active',
            'testseries_obj': testseries_obj
        })
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post("/admin/post_study_material_name/")
async def post_study_material_name(sname: str = Form(...)):
    try:
        await StudyMaterialName.create(name=sname, slug=slugify(sname))
        return RedirectResponse(url='/admin/add_study_material/', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post('/admin/add_study_material_course/', )
async def create_course(study_material_id: str = Form(...),
                        course_id: str = Form(...), icon_image=File(...),
                        bundle_price: int = Form(...), discount_price: int = Form(...), s3: BaseClient = Depends(s3_auth)):
    try:
        course_instance = await Course.get(id=course_id)
        preference = await StudyMaterialName.get(id=study_material_id)
        image_url = await upload_pdf_notes(s3, folder='study_material/course_icons', image=icon_image, mimetype=None)
        if not await StudyMaterialCourse.exists(material=preference, course=course_instance):
            await StudyMaterialCourse.create(
                material=preference, course=course_instance,
                bundle_price=bundle_price, bundle_dsc_price=discount_price, web_icon=image_url,
            )
        return RedirectResponse(url='/admin/add_study_material/', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post('/admin/add_study_material_category/', )
async def add_study_material_category(study_material_id: str = Form(...), category_name: str = Form(...),
                                      course_id: str = Form(...), chapter_name: str = Form(...),
                                      org_price: int = Form(...), d_price: int = Form(...),
                                      icon_image: UploadFile = File(...), material_file: UploadFile = File(...),
                                      s3: BaseClient = Depends(s3_auth)):
    try:
        preference = await StudyMaterialName.get(id=study_material_id)
        course = await Course.get(id=course_id)
        categoryCourse = await StudyMaterialCourse.get(course=course, material=preference)
        image_url = await upload_images(s3, folder='study_material/category_icons', image=icon_image, mimetype=None)

        material_url = await upload_images(s3, folder='study_material/notes/'+slugify(category_name), image=material_file, mimetype='application/pdf')
        image_split = material_url.split('/')[-1]
        material_url_key = 'study_material/notes/' + \
            slugify(category_name)+"/"+image_split

        await StudyMaterialCategories.create(course=categoryCourse, name=category_name, slug=slugify(category_name),
                                             topic_name=chapter_name, topic_slug=slugify(
            chapter_name),
            price=org_price, discount_price=d_price, web_icon=image_url,
            material_url_key=material_url_key
        )
        return RedirectResponse(url='/admin/add_study_material/', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post('/admin/add_study_material_test_series/', )
async def add_study_material_test_series(study_material_id: str = Form(...), category_name: str = Form(...),
                                         course_id: str = Form(...), chapter_name: str = Form(...), time_duration: str = Form(...),
                                         no_of_qstns: int = Form(...), marks: int = Form(...), test_series_thumbnail: UploadFile = File(...),
                                         lecture_test_series: UploadFile = File(...), s3: BaseClient = Depends(s3_auth)):
    try:
        preference = await StudyMaterialName.get(id=study_material_id)
        course = await Course.get(id=course_id)
        categoryCourse = await StudyMaterialCourse.get(course=course, material=preference)
        image_url = await upload_images(s3, folder='study_material/test_series_thumbnail', image=test_series_thumbnail, mimetype=None)

        lecture_filename = (lecture_test_series.filename).split(".")[-1]

        if lecture_filename == 'xlsx':

            data = pd.read_excel(
                lecture_test_series.file.read())

            test_series_instance = await StudyMaterialTestSeries.create(course=categoryCourse, cat_name=category_name, cat_slug=slugify(category_name),
                                                                        topic_name=chapter_name, topic_slug=slugify(
                                                                            chapter_name),
                                                                        time_duration=time_duration, marks=marks, no_of_qstns=no_of_qstns, thumbnail=image_url)

            for i, k in data.iterrows():
                await StudyMaterialTestSeriesQuestions.create(
                    question=k['questions'],
                    opt_1=k['opt_1'],
                    opt_2=k['opt_2'],
                    opt_3=k['opt_3'],
                    opt_4=k['opt_4'],
                    answer=k['answer'],
                    solution=k['solution'],
                    test_series=test_series_instance
                )

            return RedirectResponse(url='/admin/add_study_material/', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.delete('/admin/delete_studyMaterial/{mid}')
async def delete_studymaterial(mid: str):
    try:
        await StudyMaterialCategories.filter(id=mid).delete()
        return {"status": True}
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.delete('/admin/delete_testseries/{mid}')
async def delete_studymaterial(mid: str):
    try:
        await StudyMaterialTestSeries.filter(id=mid).delete()
        return {"status": True}
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post('/admin/get_study_material_course/')
async def get_study_material_course(request: Request):
    try:
        data = await request.json()
        mid = data['mid']
        obj = await StudyMaterialCourse.filter(material__id=mid).values("course__id","course__name")
        
        return obj
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )

# '''
# Frontend controller
# '''


@router.get('/exam_study_material/{flag}/')
async def exam_study_material(request: Request, flag: str, user=Depends(get_current_user)):
    try:
        if user is None:
            return RedirectResponse(url="/student/login/?returnURL=/exam_study_material/",
                                    status_code=status.HTTP_302_FOUND)
        if await StudyMaterialName.exists(slug=flag):
            std_obj = await StudyMaterialName.get(slug=flag)
            std_material_id = std_obj.id

        else:
            raise HTTPException(detail="Bad Request", status_code=208)
        category_course_obj = await StudyMaterialCourse_Pydantic.from_queryset(
            StudyMaterialCourse.filter(material__id=std_material_id)
        )

        return frontend_templates.TemplateResponse('exam_study_material.html', context={
            'request': request,
            'category_course': category_course_obj,
            'flag': flag,
        })
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/exam_study_notes/{id}/')
async def exam_study_material(request: Request, id: str, user=Depends(get_current_user)):
    try:
        if user is None:
            return RedirectResponse(url="/student/login/?returnURL=/exam_study_notes/" + id + "/",
                                    status_code=status.HTTP_302_FOUND)
        # cat_instance = await StudyMaterialCategories.get(id=id)
        course_instance = await StudyMaterialCourse.get(id=id).values('course__name')
        c_name = course_instance['course__name']

        course_categories = await StudyMaterialCategories_Pydantic.from_queryset(
            StudyMaterialCategories.filter(course__id=id)
        )
        return frontend_templates.TemplateResponse('view_notes.html', context={
            'request': request,
            'course_categories': course_categories,
            'c_name': c_name,
            'cid': id,

        })
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/testseries/{id}/')
async def view_test_series(request: Request, id: str,  user=Depends(get_current_user)):
    try:
        course_instance = await StudyMaterialCourse.get(id=id).values('course__name')
        c_name = course_instance['course__name']
        test_series_obj = await StudyMaterialTestSeries_Pydantic.from_queryset(
            StudyMaterialTestSeries.filter(course__id=id)
        )

        category_course_obj = await StudyMaterialCourse_Pydantic.from_queryset_single(
            StudyMaterialCourse.get(id=id)
        )
        student = await Student.get(id=user)
        # return test_series_obj
        return frontend_templates.TemplateResponse('view_testseries.html', context={
            'request': request,
            'app_url': app_url,
            'c_name': c_name,
            'test_series_obj': test_series_obj,
            'category_course': category_course_obj,
            'student_name': student.fullname,
            'email': student.email,
            'mobile': student.mobile,
            'student_id': student.id,
            'subscription_id': id,
            'razorpay_key': razorpay_key

        })
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.get('/exam_study_material/checkout/{cat_id}/')
async def exam_study_material(request: Request, cat_id: str, user=Depends(get_current_user)):
    try:
        if user is None:
            return RedirectResponse(url="/student/login/?returnURL=/exam_study_material/",
                                    status_code=status.HTTP_302_FOUND)
        if await StudyMaterialCategories.exists(id=cat_id):

            if await Student.exists(id=user):
                student = await Student.get(id=user)
                item_instance = await StudyMaterialCategories.get(id=cat_id)
                if await StudyMaterialCartInstance.exists(student=student):
                    await StudyMaterialCartInstance.filter(student=student).delete()
                    await StudyMaterialCartInstance.create(student=student, item_id=item_instance)
                else:
                    await StudyMaterialCartInstance.create(student=student, item_id=item_instance)

            else:
                return RedirectResponse(url="/student/login/?returnURL=/exam_study_material/",
                                        status_code=status.HTTP_302_FOUND)

            course_categories = await StudyMaterialCategories_Pydantic.from_queryset_single(
                StudyMaterialCategories.get(id=cat_id)
            )

            return frontend_templates.TemplateResponse('checkout.html', context={
                'request': request,
                'app_url': app_url,
                'category_course': course_categories,
                'student_name': student.fullname,
                'email': student.email,
                'mobile': student.mobile,
                'razorpay_key': razorpay_key,
                'student_id': user,
                'subscription_id': cat_id
            })
        else:
            raise HTTPException(status_code=208, detail="Instance not found")
    except Exception as e:
        # raise HTTPException(detail=str(e), status_code=208)
        return RedirectResponse(url="/student/login/", status_code=status.HTTP_302_FOUND)


@router.post('/create_test_series_order_id/')
async def create_order_id(request: Request, user=Depends(get_current_user)):
    try:
        data = await request.json()
        amount = int(data['amount'])
        subscription_id = data['subscription_id']
        if not await TestSeriesOrders.exists(student__id=user, test_series_id=subscription_id):

            order = client.order.create({
                "amount": amount * 100,
                "currency": "INR",
                "receipt": 'order_rcptid_11'
            })

            return JSONResponse({"status": True, "order_id": order['id']}, status_code=200)
        else:
            return JSONResponse({"status": False, "message": "You've already purchased this test series"})
    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


@router.post('/test_series_place_order/')
async def create_test_series_order(request: Request, user=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)
        student = await Student.get(id=user)
        data = await request.json()
        ts_instance = await StudyMaterialCourse.get(id=data["series_id"])
        order = await TestSeriesOrders.create(
            student=student,
            test_series=ts_instance,
            razorpay_payment_id=data["razorpay_payment_id"],
            razorpay_order_id=data["razorpay_order_id"],
            razorpay_signature=data["razorpay_signature"],
            bill_amount=data["amount"],
            updated_at=updated_at,
            created_at=updated_at,

        )
        return {"status": True, "detail": 'order placed successfully',
                'redirectUrl': '/student/new-dashboard/'}
    except Exception as ex:

        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


@router.post('/submit_order/')
async def create_razorpay_order(request: Request,
                                create_order: Optional[str] = None, place_order: Optional[str] = None,
                                user=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)

        student = await Student.get(id=user)
        if await StudyMaterialCartInstance.exists(student=student):
            cart_instance = await StudyMaterialCartInstance.get(student=student).values("item_id__id")
            item_id = cart_instance["item_id__id"]
            item_instance = await StudyMaterialCategories.get(id=item_id)
            amount = item_instance.discount_price
            # await StudyMaterialOrderInstance.filter(student=student, item_id=item_instance).delete()

            if not await StudyMaterialOrderItems.exists(order__student=student, item_id=item_instance):

                if create_order == 'True':
                    order = client.order.create({
                        "amount": amount * 100,
                        "currency": "INR",
                        "receipt": 'order_rcptid_11'
                    })

                    return JSONResponse({"status": True, "order_id": order['id']}, status_code=200)

                if place_order == 'True':
                    data = (await request.json())
                    params_dict = data
                    razorpay_verify = client.utility.verify_payment_signature(
                        params_dict)

                    # # print(order)
                    # print("============================order_id here================")

                    order = await StudyMaterialOrderInstance.create(
                        student=student, item_id=item_instance,
                        razorpay_payment_id=data['razorpay_payment_id'],
                        razorpay_order_id=data['razorpay_order_id'],
                        razorpay_signature=data['razorpay_signature'],
                        bill_amount=item_instance.discount_price,
                        updated_at=updated_at, created_at=updated_at
                    )

                    await StudyMaterialOrderItems.create(
                        order=order,
                        item_id=item_instance,
                        updated_at=updated_at,
                        created_at=updated_at
                    )

                    return {"status": True, "detail": 'order placed successfully',
                            'redirectUrl': '/student/new-dashboard/'}

            else:
                return JSONResponse({"status": False,
                                    "detail": "You've already purchased this content"}, status_code=208)
        else:
            return JSONResponse({"status": False, "details": "Student Id does not exist"}, status_code=208)

    except Exception as ex:
        return JSONResponse(
            {"status": False, "message": str(ex)}, status_code=208
        )


class OrderParams(BaseModel):
    student_id: uuid.UUID
    item_id: str
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: Optional[str] = None
    bill_amount: int


@router.post('/study_material_order/')
async def create_order(data: OrderParams,):
    try:
        updated_at = datetime.now(tz)

        await StudyMaterialOrderInstance.create(
            student=data.student_id, item_id=data.item_id,
            razorpay_payment_id=data.razorpay_payment_id,
            razorpay_order_id=data.razorpay_order_id,
            razorpay_signature=data.razorpay_signature,
            bill_amount=data.bill_amount, updated_at=updated_at,
            created_at=updated_at
        )

        return JSONResponse({"status": True, "message": "Order Created."}, status_code=200)
    except Exception as ex:

        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)
