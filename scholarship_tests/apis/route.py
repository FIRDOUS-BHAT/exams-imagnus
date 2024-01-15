import numpy as np
from fastapi.encoders import jsonable_encoder
import pytz
from fastapi import APIRouter, Depends, UploadFile, File
from datetime import datetime
from utils.util import get_current_user
from cache_config import cache
from aiocache import cached

from starlette.responses import JSONResponse
from scholarship_tests.models import ScholarshipTestSeries, ScholarshipTestSeries_Pydantic, ScholarshipTestSeriesQuestions, StudentScholarshipTestSeriesRecord
from scholarship_tests.pydantic_models import rankPydantic, rankResponsePydantic, studentIdPydanctic, testRecordIn_Pydantic
from student.models import Student
'''Scholarship testseries here'''


router = APIRouter()


tz = pytz.timezone('Asia/Kolkata')


@router.post('/v1/scholarship/2022/')
async def scholarship(data: studentIdPydanctic):
    student_id = data.student_id
    course_id = data.course_id
    lang = data.lang
    test_obj = await ScholarshipTestSeries.get(course__id=course_id, lang=lang)
    updated_at = datetime.now(tz)
    if await Student.exists(id=student_id):
        test_series_id = None
        student = await Student.get(id=student_id)
        if await StudentScholarshipTestSeriesRecord.exists(student=student, test_series__course__id=course_id, is_attempted=True):
            if await ScholarshipTestSeries.filter(lang=lang, course__id=course_id, result_announcement_date__lte=updated_at):

                status = 'announced'
                test_series_id = test_obj.id
            else:
                status = 'attempted'
        else:
            if await ScholarshipTestSeries.filter(lang=lang, course__id=course_id, on_date__lte=updated_at, end_date__gte=updated_at):
                status = 'online'
                test_series_id = test_obj.id
            elif await ScholarshipTestSeries.filter(lang=lang, course__id=course_id, on_date__gt=updated_at):
                status = 'not_yet_started'
            elif await ScholarshipTestSeries.filter(lang=lang, course__id=course_id, end_date__lt=updated_at):
                status = 'not_attempted'
            else:
                status = 'not_attempted'
        message = {
            "title": test_obj.title,
            "banner": test_obj.image,
            "status": status,
            "testseries_start_time": test_obj.on_date,
            "server_time": updated_at,
            "description": test_obj.description,
            "testseries_id": test_series_id
        }

        return JSONResponse({"status": True, "message": jsonable_encoder(message)}, status_code=200)
    return JSONResponse({"status": False, "message": "Student not registered"}, status_code=208)
    # if not await StudentScholarshipTestSeriesRecord.exists(student=student, is_attempted=True):

    # else:
    #             return JSONResponse({"status": False, "message": "You've already made an attempt"}, status_code=208)

    return JSONResponse({''})


@router.post('/v1/scholarship/testseries/')
async def scholarship_testseries(data: studentIdPydanctic,  _=Depends(get_current_user)):
    student_id = data.student_id
    course_id = data.course_id
    lang = data.lang

    if await Student.exists(id=student_id):
        student = await Student.get(id=student_id)
        updated_at = datetime.now(tz)

        if await ScholarshipTestSeries.exists(lang=lang, course__id=course_id, on_date__lte=updated_at):
            if not await StudentScholarshipTestSeriesRecord.exists(student=student, test_series__course__id=course_id, is_attempted=True):

                test_obj = await ScholarshipTestSeries_Pydantic.from_queryset_single(
                    ScholarshipTestSeries.get(lang=lang, course__id=course_id))

                return JSONResponse({"status": True, "message": jsonable_encoder(test_obj)}, status_code=200)
            else:
                return JSONResponse({"status": False, "message": "You've already attempted."}, status_code=208)
        else:
            return JSONResponse({"status": False, "message": "No Test available at this time"}, status_code=208)


@router.post('/v1/scholarship/submit_test_record/')
async def add_test_records(data: testRecordIn_Pydantic, _=Depends(get_current_user)):
    student_id = data.student_id
    test_series_id = data.test_series_id
    correct_ans = data.correct_ans
    wrong_ans = data.wrong_ans
    time_taken = data.time_taken
    skipped_qns = data.skipped_qns
    test_record_summary = data.test_record_summary
    if await Student.exists(id=student_id):
        student = await Student.get(id=student_id)
        if await ScholarshipTestSeries.exists(id=test_series_id):
            test_series = await ScholarshipTestSeries.get(id=test_series_id)
            marks = ((test_series.total_marks) /
                     (test_series.no_of_qstns)) * correct_ans
            if not await StudentScholarshipTestSeriesRecord.exists(test_series=test_series, student=student):
                await StudentScholarshipTestSeriesRecord.create(
                    student=student,
                    test_series=test_series,
                    correct_ans=correct_ans,
                    wrong_ans=wrong_ans,
                    skipped_qns=skipped_qns,
                    marks=marks,
                    time_taken=time_taken,
                    is_attempted=True,
                    test_record_summary=test_record_summary,
                )
                return JSONResponse(
                    {"status": True, "message": "Submitted"}, status_code=201)
            else:
                return JSONResponse(
                    {"status": False, "message": "You're not allowed to re-submit this test series"}, status_code=208)
        return JSONResponse({"status": False, "message": "Series doesn't exist."}, status_code=208)

    return JSONResponse({"status": False, "message": "Student not registered"}, status_code=208)


@router.put('/update_start_time/')
async def update_start_time(test_series_id: str, start_time: datetime):
    obj = await ScholarshipTestSeries.filter(id=test_series_id).update(on_date=start_time)
    return {"date modified"}


@router.delete('/delete_all submitted_scholarship_records/')
async def delete_all_submitted_scholarship_records():
    await StudentScholarshipTestSeriesRecord.all().delete()
    return {"All data deleted."}


@router.put('/update_announcement_date/')
async def update_announcement_date(test_series_id: str, announcement_time: datetime):
    obj = await ScholarshipTestSeries.filter(id=test_series_id).update(result_announcement_date=announcement_time)
    return {"date modified"}


def custom_key_builder(func, *args, **kwargs):
    # Extract student_id from kwargs
    student_id = 'default'
    if 'data' in kwargs and hasattr(kwargs['data'], 'student_id'):
        student_id = kwargs['data'].student_id
        
    return f"{func.__module__}:{func.__name__}:{student_id}"


                           
@router.post('/get_students_rank/', response_model=rankResponsePydantic)
@cached(key_builder=custom_key_builder)

async def get_students_rank(data: rankPydantic, _=Depends(get_current_user)):
    student_id = data.student_id
     
    if await StudentScholarshipTestSeriesRecord.exists(student__id=student_id, is_attempted=True):
        
        test_obj = await StudentScholarshipTestSeriesRecord.get(
        student__id=student_id, is_attempted=True
         )
        updated_at = datetime.now(tz)
        if await ScholarshipTestSeries.exists(id=test_obj.test_series_id, result_announcement_date__lte=updated_at):
            test_series_obj = await ScholarshipTestSeries.get(id=test_obj.test_series_id)
            test_series_questions = await ScholarshipTestSeriesQuestions.filter(test_series__id=test_obj.test_series_id)

            result_obj = await StudentScholarshipTestSeriesRecord.get(
                student__id=student_id, test_series__id=test_obj.test_series_id)
            rank_query = await StudentScholarshipTestSeriesRecord.filter(test_series__id=test_obj.test_series_id).order_by('-marks', 'time_taken')
            top_ten = await StudentScholarshipTestSeriesRecord.filter(test_series__id=test_obj.test_series_id).order_by('-marks', 'time_taken').limit(10).values("id", "marks", "time_taken", "student_id", "test_series_id", student_name="student__fullname")
            np_arr = np.array(rank_query)
            index_of_student = 0
            for i in range(np_arr.size):

                if str(np_arr[i].student_id) == str(student_id):

                    index_of_student = i
                    break

            new_dict = jsonable_encoder(test_series_obj)
            new_dict.update(
                {"ScholarshipTestSeries": test_series_questions})
            new_dict.update(
                {"ScholarshipTestSeries_student": result_obj})

            message = {
                "rank": str(index_of_student)+'/'+str(len(rank_query)),
                "top_ten": jsonable_encoder(top_ten),

                # "correct_ans": result_obj.correct_ans,
                # "wrong_ans": result_obj.wrong_ans,
                # "skipped_qns": result_obj.skipped_qns,
                # "time_taken": result_obj.time_taken,
                "test_series_obj": jsonable_encoder(new_dict),
                # "test_record_summary": result_obj.test_record_summary,
            }
            return JSONResponse({"status": True, "message": message}, status_code=200)
        else:
            return JSONResponse({"status": True, "message": "No data Found"}, status_code=208)
    else:
        return JSONResponse({"status": False, "message": "No student data Found"}, status_code=208)
