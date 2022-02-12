from admin_dashboard.apis.route import DashboardPydantic
from student.models import Student
import boto3
import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from study_material.apis.pydantic_models import OrderParams, StudyMaterialNotes, StudyMaterialScreen, \
    StudyMaterialScreenV1, StudyMaterialTesSeriesBundlePydantic, StudyMaterialTestSeriesPydantic, \
    TestSeriesBundleInputParams, TestSeriesInputParams, TestSeriesOrder, TestSeriesOrderHistory, TestSeriesQuestions, \
    orderHistoryPydactic
from study_material.models import StudyMaterialCategories, StudyMaterialCategories_Pydantic, StudyMaterialCourse, \
    StudyMaterialCourse_Pydantic, StudyMaterialName, StudyMaterialName_Pydantic, StudyMaterialOrderInstance, \
    StudyMaterialOrderInstance_Pydantic, StudyMaterialOrderItems, StudyMaterialTestSeries, \
    StudyMaterialTestSeries_Pydantic, StudyMaterialTestSeriesQuestions, TestSeriesOrders, TestSeriesOrders_Pydantic
from typing import List
from utils.util import get_current_user
from starlette.requests import Request
import razorpay
from functools import lru_cache
from configs import appinfo
import pytz
from datetime import datetime
from botocore.client import Config

tz = pytz.timezone('Asia/Kolkata')

router = APIRouter()


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()
razorpay_key = settings.razorpay_key
razorpay_secret = settings.razorpay_secret
app_name = settings.app_name
app_version = settings.app_version
client = razorpay.Client(auth=(razorpay_key, razorpay_secret))


class OrderIdPydantic(BaseModel):
    amount: int


@router.post('/create_razorpay_order_id/')
async def create_order_id(data: OrderIdPydantic, _=Depends(get_current_user)):
    order = client.order.create({
        "amount": data.amount * 100,
        "currency": "INR",
        "receipt": 'order_rcptid_11'
    })
    return JSONResponse({"status": True, "order_id": order['id']}, status_code=200)


@router.get('/study_material_labels/{course_id}/{student_id}/',
            response_model=StudyMaterialScreen
            )
async def study_material_labels(course_id: str, student_id: str, user=Depends(get_current_user)):
    try:
        # obj = await StudyMaterialName_Pydantic.from_queryset(StudyMaterialName.all())
        obj = await StudyMaterialName.all()
        material_array = []
        main_array = {}
        for material in obj:
            material_array.append(
                {"label_id": material.id, "label": material.name}
            )

        if await StudyMaterialCategories.exists(course__material__id=material_array[0]["label_id"],
                                                course__course__id=course_id):
            content_count = await StudyMaterialCategories.filter(
                course__material__id=material_array[0]["label_id"], course__course__id=course_id).count()

            material_array[0].update({"count": content_count})
        else:
            material_array[0].update({"count": 0})

        if await StudyMaterialTestSeries.exists(course__material__id=material_array[1]["label_id"],
                                                course__course__id=course_id):
            content_count = await StudyMaterialTestSeries.filter(
                course__material__id=material_array[1]["label_id"], course__course__id=course_id).count()

            material_array[1].update({"count": content_count})
        else:
            material_array[1].update({"count": 0})

        main_array.update({"content": material_array})

        course_categories = await StudyMaterialCategories_Pydantic.from_queryset(
            StudyMaterialCategories.filter(course__course__id=course_id)
        )
        new_array = []
        for item in course_categories:
            new_dict = item.dict()
            item_id = item.id
            if await StudyMaterialOrderItems.exists(item_id=item_id, order__student__id=student_id):
                new_dict.update({'is_purchased': True})
            else:
                new_dict.update({'is_purchased': False})

            new_array.append(new_dict)

        main_array.update({"recommendedNotes": new_array})

        return main_array
    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


@router.get('/study_material_labels/v1/{course_id}/{student_id}/',
            response_model=StudyMaterialScreenV1
            )
async def study_material_labels(course_id: str, student_id: str, user=Depends(get_current_user)):
    try:
        # obj = await StudyMaterialName_Pydantic.from_queryset(StudyMaterialName.all())
        obj = await StudyMaterialName.all()
        material_array = []
        main_array = {}

        for material in obj:
            material_array.append(
                {"label_id": material.id, "label": material.name}
            )

        if await StudyMaterialCategories.exists(course__material__id=material_array[0]["label_id"],
                                                course__course__id=course_id):
            content_count = await StudyMaterialCategories.filter(
                course__material__id=material_array[0]["label_id"], course__course__id=course_id).count()

            material_array[0].update({"count": content_count})
        else:
            material_array[0].update({"count": 0})

        if await StudyMaterialTestSeries.exists(course__material__id=material_array[1]["label_id"],
                                                course__course__id=course_id):
            content_count = await StudyMaterialTestSeries.filter(
                course__material__id=material_array[1]["label_id"], course__course__id=course_id).count()

            material_array[1].update({"count": content_count})
        else:
            material_array[1].update({"count": 0})

        main_array.update({"content": material_array})

        course_categories = await StudyMaterialCategories_Pydantic.from_queryset(
            StudyMaterialCategories.filter(
                course__course__id=course_id).limit(5)
        )

        new_array = []
        for item in course_categories:
            new_dict = item.dict()
            item_id = item.id
            if await StudyMaterialOrderItems.exists(item_id=item_id, order__student__id=student_id):
                new_dict.update({'is_purchased': True})
            else:
                new_dict.update({'is_purchased': False})

            new_array.append(new_dict)

        main_array.update({"recommendedNotes": new_array})
        test_series_obj = await StudyMaterialTestSeries_Pydantic.from_queryset(
            StudyMaterialTestSeries.filter(
                course__course__id=course_id).limit(5)
        )
        if await TestSeriesOrders.exists(student__id=student_id, test_series__course__id=course_id):
            is_purchased = {'is_purchased': True}
        else:
            is_purchased = {'is_purchased': False}

        new_test_series = []
        for series_item in test_series_obj:
            new_series_dict = series_item.dict()
            new_series_dict.update(is_purchased)
            new_test_series.append(new_series_dict)
        main_array.update({"recommendedTestSeries": new_test_series})

        return main_array
    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


@router.get('/exam_study_material/pdf/{course_id}/{student_id}/', response_model=List[StudyMaterialNotes])
async def exam_study_material(request: Request, course_id: str, student_id: str, user=Depends(get_current_user)):
    course_categories = await StudyMaterialCategories_Pydantic.from_queryset(
        StudyMaterialCategories.filter(course__course__id=course_id)
    )
    new_array = []
    '''new code starts with '''

    '''new code ends'''

    for content in course_categories:
        new_dict = content.dict()
        item_id = content.id

        if await StudyMaterialOrderItems.exists(order__student__id=student_id, order__package_mode=2):
            new_dict.update({'is_purchased': True})

        elif await StudyMaterialOrderItems.exists(order__student__id=student_id, order__package_mode=1):
            if await StudyMaterialOrderItems.exists(item_id=item_id, order__student__id=student_id):
                new_dict.update({'is_purchased': True})
            else:
                new_dict.update({'is_purchased': False})
        else:
            new_dict.update({'is_purchased': False})
        new_array.append(new_dict)
    return new_array


class MaterialPackage(BaseModel):
    id: uuid.UUID
    web_icon: str
    bundle_price: int
    bundle_dsc_price: int
    StudyMaterialCourse: List[StudyMaterialNotes]


@router.get('/exam_study_material/package/{course_id}/{student_id}/',
            response_model=List[MaterialPackage]
            )
async def material_package(course_id: str, student_id: str, user=Depends(get_current_user)):
    obj = await StudyMaterialCourse_Pydantic.from_queryset(
        StudyMaterialCourse.filter(course__id=course_id)
    )
    new_list = []
    new_array = []
    for each in obj:
        updated_dict = each.dict()
        for mat in each.StudyMaterialCourse:
            new_dict = mat.dict()
            item_id = mat.id
            if await StudyMaterialOrderItems.exists(order__student__id=student_id, order__package_mode=2):
                new_dict.update({'is_purchased': True})

            elif await StudyMaterialOrderItems.exists(order__student__id=student_id, order__package_mode=1):
                if await StudyMaterialOrderItems.exists(item_id=item_id, order__student__id=student_id):
                    new_dict.update({'is_purchased': True})
                else:
                    new_dict.update({'is_purchased': False})
            else:
                new_dict.update({'is_purchased': False})

            new_array.append(new_dict)
        updated_dict.update({'StudyMaterialCourse': new_array})
        new_list.append(updated_dict)
    return new_list


'''
@router.get('/exam_study_notes/{id}/', response_model=List[StudyMaterialNotes])
async def exam_study_notes(request: Request, id: str, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/student/login/?returnURL=/exam_study_notes/" + id + "/",
                                status_code=status.HTTP_302_FOUND)
    # cat_instance = await StudyMaterialCategories.get(id=id)
    course_instance = await StudyMaterialCourse.get(id=id).values('course__name')
    c_name = course_instance[0]['course__name']
   
    course_categories = await StudyMaterialCategories_Pydantic.from_queryset(
        StudyMaterialCategories.filter(course__id=id)
    )
    
    return course_categories
'''


@router.post('/study_material_order/')
async def create_study_material_order(data: OrderParams, user=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)
        student = await Student.get(id=data.student_id)
        order = await StudyMaterialOrderInstance.create(
            student=student,
            razorpay_payment_id=data.razorpay_payment_id,
            razorpay_order_id=data.razorpay_order_id,
            bill_amount=data.bill_amount,
            package_mode=data.package_mode,

        )
        for item_id in data.item_id:
            item = await StudyMaterialCategories.get(id=item_id)
            await StudyMaterialOrderItems.create(
                order=order,
                item_id=item,

            )

        return JSONResponse({"status": True, "message": "Order Created."}, status_code=200)
    except Exception as ex:

        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


aws_access_key_id = settings.AWS_SERVER_PUBLIC_KEY
aws_secret_access_key = settings.AWS_SERVER_SECRET_KEY
aws_region = settings.AWS_SERVER_REGION


class studyMaterialUrl(BaseModel):
    student_id: uuid.UUID
    material_id: uuid.UUID


@router.post('/study_material_url/', )
async def get_signed_url(data: studyMaterialUrl, user: str = Depends(get_current_user)):
    try:

        if await StudyMaterialOrderItems.exists(order__student__id=data.student_id, order__package_mode=2):

            material_instance = await StudyMaterialCategories.get(id=data.material_id)
            material_url_key = material_instance.material_url_key

            s3Client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                config=Config(signature_version='s3v4'),
                region_name=aws_region,
            )
            presigned_url = s3Client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': 'testing-bucket-s3-uploader',
                    'Key': material_url_key
                },
                ExpiresIn=600)

            # item_id__id=data.material_id
            return JSONResponse({'status': True, 'message': presigned_url})
        elif await StudyMaterialOrderItems.exists(order__student__id=data.student_id, order__package_mode=1):
            if await StudyMaterialOrderItems.exists(order__student__id=data.student_id, item_id__id=data.material_id):
                material_instance = await StudyMaterialCategories.get(id=data.material_id)
                material_url_key = material_instance.material_url_key

                s3Client = boto3.client(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    config=Config(signature_version='s3v4'),
                    region_name=aws_region,
                )
                presigned_url = s3Client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': 'testing-bucket-s3-uploader',
                        'Key': material_url_key
                    },
                    ExpiresIn=600)

                return JSONResponse({'status': True, 'message': presigned_url})
            else:
                return JSONResponse({'status': False, 'message': 'Wrong Input'})
        else:
            return JSONResponse({'status': False, 'message': 'Wrong Input'})
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)})


@router.post('/study_material_order_history/',
             response_model=List[orderHistoryPydactic]
             )
async def order_history(data: DashboardPydantic, user=Depends(get_current_user)):
    student_id = data.student_id
    obj = await StudyMaterialOrderInstance_Pydantic.from_queryset(
        StudyMaterialOrderInstance.filter(student__id=student_id)
    )
    return obj


"""@router.get('/get_all_study_material_courses/') 
async def get_all():
    return await StudyMaterialCourse.all()"""


@router.put('/update_study_material_course_price/{mid}/{original_price}/{discount_price}/')
async def update_prices(mid: str, original_price: int, discount_price: int):
    await StudyMaterialCourse.filter(id=mid).update(
        bundle_price=original_price, bundle_dsc_price=discount_price)
    return {"update done"}


@router.post('/exam_study_material/test_series/package/',
             response_model=List[StudyMaterialTesSeriesBundlePydantic]
             )
async def exam_test_series_bundle(data: TestSeriesBundleInputParams, user=Depends(get_current_user)):
    course_categories = await StudyMaterialCourse_Pydantic.from_queryset(
        StudyMaterialCourse.filter(
            course__id=data.course_id, material__id=data.label_id)
    )
    new_array = []
    for content in course_categories:
        new_dict = content.dict()
        item_id = content.id
        if await TestSeriesOrders.exists(test_series=item_id, student__id=data.student_id):
            new_dict.update({'is_purchased': True})
        else:
            new_dict.update({'is_purchased': False})

        new_array.append(new_dict)
    return new_array


@router.post('/exam_study_material/test_series/',
             response_model=List[StudyMaterialTestSeriesPydantic]
             )
async def exams_test_series(data: TestSeriesInputParams, user=Depends(get_current_user)):
    obj = await StudyMaterialTestSeries_Pydantic.from_queryset(
        StudyMaterialTestSeries.filter(course__id=data.bundle_id)
    )

    return obj


@router.post('/test_series_place_order/')
async def create_test_series_order(data: TestSeriesOrder, user=Depends(get_current_user)):
    try:
        updated_at = datetime.now(tz)
        student = await Student.get(id=data.student_id)
        ts_instance = await StudyMaterialCourse.get(id=data.item_id)
        order = await TestSeriesOrders.create(
            student=student,
            test_series=ts_instance,
            razorpay_payment_id=data.razorpay_payment_id,
            razorpay_order_id=data.razorpay_order_id,
            bill_amount=data.bill_amount,
            updated_at=updated_at,
            created_at=updated_at,

        )

        return JSONResponse({"status": True, "message": "Order Created."}, status_code=200)
    except Exception as ex:

        return JSONResponse({"status": False, "message": str(ex)}, status_code=208)


class EachTestSeriesPydanctic(BaseModel):
    student_id: str
    series_id: str


@router.post('/get_each_test_series/',
             response_model=List[TestSeriesQuestions]
             )
async def each_test_series(data: EachTestSeriesPydanctic, user=Depends(get_current_user)):
    obj = await StudyMaterialTestSeriesQuestions.filter(test_series=data.series_id)
    return obj


@router.post('/get_test_series_order_history/',
             response_model=List[TestSeriesOrderHistory]
             )
async def test_series_order_history(data: DashboardPydantic, user=Depends(get_current_user)):
    obj = await TestSeriesOrders_Pydantic.from_queryset(
        TestSeriesOrders.filter(student__id=data.student_id)
    )

    return obj
