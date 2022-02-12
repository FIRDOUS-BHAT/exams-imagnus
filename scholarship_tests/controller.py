from starlette import status
from starlette.responses import JSONResponse, RedirectResponse
from scholarship_tests.pydantic_models import rankPydantic
from student.models import Student
from student.controller import get_current_user, inputQstnsQuiz
from scholarship_tests.models import ScholarshipTestSeries, ScholarshipTestSeriesQuestions, ScholarshipTestSeriesQuestions_Pydantic, StudentScholarshipTestSeriesRecord, StudentScholarshipTestSeriesRecord_Pydantic
from fastapi.routing import APIRouter
from starlette.requests import Request
from starlette.templating import Jinja2Templates
from fastapi import Depends

templates = Jinja2Templates(directory="scholarship_tests/templates")

router = APIRouter()


@router.get('/scholarship/test/instructions/', )
async def test_instructions(request: Request, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/student/login/?returnURL=/scholarship/test/instructions/",
                                status_code=status.HTTP_302_FOUND)
    student_instance = await Student.get(id=user)
    studentName = student_instance.fullname
    return templates.TemplateResponse('instructions.html', context={
        'request': request,
        'studentName': studentName

    })


@router.get('/scholarship/test/')
async def test_instructions(request: Request, lang: str, user=Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/student/login/?returnURL=/scholarship/test/instructions/",
                                status_code=status.HTTP_302_FOUND)
    student_instance = await Student.get(id=user)
    studentName = student_instance.fullname
    if not await StudentScholarshipTestSeriesRecord.exists(student__id=user,):
        if await ScholarshipTestSeries.exists(lang=lang):
            qstn_count = await ScholarshipTestSeriesQuestions.filter(test_series__lang=lang).count()
            if qstn_count:
                qstns = await ScholarshipTestSeriesQuestions_Pydantic.from_queryset(
                    ScholarshipTestSeriesQuestions.filter(
                        test_series__lang=lang).limit(2)
                )

                test_series = await ScholarshipTestSeries.filter(lang=lang)
                test_series_id = test_series[0].id

                test_time = test_series[0].time_duration
                # await StudentScholarshipTestSeriesRecord.filter(student__id=user).delete()
                return templates.TemplateResponse('begin_test.html', context={
                    'request': request,
                    'counter': 0,
                    'test_id': test_series_id,
                    'qstns': qstns,
                    'qstn_count': qstn_count,
                    'time_duration': test_time,
                    'lang': lang,
                    'studentName': studentName

                })
    else:
        return RedirectResponse(url="/student/scholarship/result/", status_code=status.HTTP_302_FOUND)


@router.post('/student/scholarship/testSeriesQstns/{test_id}/{cur_qstn_id}/{nx_qstn_id}/{lang}/{counter}/')
async def scholarship_test_attempt(test_id: str, cur_qstn_id: str, nx_qstn_id: str, lang: str, counter: int,
                                   data: inputQstnsQuiz,
                                   user=Depends(get_current_user),):
    try:
        student_instance = await Student.get(id=user)
        test_instance = await ScholarshipTestSeries.get(id=test_id)
        test_series_qstns_instance = await ScholarshipTestSeriesQuestions_Pydantic.from_queryset(
            ScholarshipTestSeriesQuestions.filter(test_series__lang=lang)
        )
        qstn_instance = await ScholarshipTestSeriesQuestions.get(
            id=cur_qstn_id)

        if not await StudentScholarshipTestSeriesRecord.exists(student=student_instance,):
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

            await StudentScholarshipTestSeriesRecord.create(
                test_series=test_instance,
                student=student_instance,
                correct_ans=correct_ans,
                wrong_ans=wrong_ans,
                skipped_qns=skipped_qns,
                lang_chosen=lang,
                marks=marks,
            )

        else:
            record_instance = await StudentScholarshipTestSeriesRecord.get(
                student=student_instance,
            )
            if record_instance.lang_chosen == lang:
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

            else:
                return {'status': False, 'message': "Something went wrong"}

        if nx_qstn_id == 'null':
            return {'status': False, 'message': "You're on last question, submit the test series now"}
        else:

            qstn_instance = await ScholarshipTestSeriesQuestions.get(
                id=nx_qstn_id
            )

            test_series = await ScholarshipTestSeries.filter(lang=lang).values('no_of_qstns')

            qstn_nos = test_series[0]['no_of_qstns']

            qstn_content = {
                "id": qstn_instance.id,
                "qstn": qstn_instance.question,
                "opt_1": qstn_instance.opt_1,
                "opt_2": qstn_instance.opt_2,
                "opt_3": qstn_instance.opt_3,
                "opt_4": qstn_instance.opt_4,

            }

        if counter <= qstn_nos:

            counter += 1

            if qstn_nos - counter == 1:
                result = {'status': True,
                          "qstn_content": qstn_content,
                          'test_id': test_id,
                          'nx': None,
                          'lang': lang,
                          'counter': counter}
            else:
                nx_qsn = test_series_qstns_instance[counter].id
                result = {'status': True,
                          'test_id': test_id,
                          "qstn_content": qstn_content, 'nx': nx_qsn,
                          'lang': lang,
                          'counter': counter}
        else:
            result = {
                'status': False, 'message': "You're on last question, submit the test series now"}
        return result

    except Exception as ex:
        return JSONResponse({"message": str(ex)}, status_code=208, )


'''view test series summary'''


@router.post('/student/scholarship/testseries/summary/{lang}/')
async def get_testseries_summary(lang: str, user: str = Depends(get_current_user)):

    summary = await StudentScholarshipTestSeriesRecord.filter(student__id=user)

    test_series = await ScholarshipTestSeries.filter(lang=lang).values('no_of_qstns')

    qstn_nos = test_series[0]['no_of_qstns']

    attempted = summary[0].correct_ans + summary[0].wrong_ans
    skipped = summary[0].skipped_qns
    not_visited = qstn_nos - (attempted+skipped)
    arr = {"attempted": attempted,
           "skipped": skipped,
           "not_visited": not_visited
           }
    return arr


@router.post('/submit/scholarship/testseries/')
async def submit_testseries(request: Request, user: str = Depends(get_current_user)):
    try:
        student = await StudentScholarshipTestSeriesRecord.get(student__id=user)
        student.is_attempted = True
        await student.save()
        return RedirectResponse(url="/student/scholarship/result/", status_code=status.HTTP_302_FOUND)

    except Exception:
        return RedirectResponse(url="/student/scholarship/result/", status_code=status.HTTP_302_FOUND)


@router.get('/student/scholarship/result/')
async def student_test_result(request: Request, user: str = Depends(get_current_user)):
    if user is None:
        return RedirectResponse(url="/student/login/?returnURL=/scholarship/test/instructions/",
                                status_code=status.HTTP_302_FOUND)

    if await StudentScholarshipTestSeriesRecord.exists(student__id=user):

        summary = await StudentScholarshipTestSeriesRecord.filter(student__id=user)

        test_series = await ScholarshipTestSeries.all().values('no_of_qstns')

        qstn_nos = test_series[0]['no_of_qstns']

        attempted = summary[0].correct_ans + summary[0].wrong_ans
        skipped = summary[0].skipped_qns
        not_visited = qstn_nos - (attempted+skipped)
        arr = {"correct": summary[0].correct_ans,
               "wrong_ans": summary[0].wrong_ans,
               "skipped": skipped,
               "not_visited": not_visited + skipped
               }
        return templates.TemplateResponse('student_test_result.html', context={
            'request': request,
            'result_details': arr,
            'total_qstns': qstn_nos
        })

    else:
        return RedirectResponse(url="/scholarship/test/instructions/", status_code=status.HTTP_302_FOUND)
