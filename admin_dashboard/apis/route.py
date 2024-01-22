from datetime import datetime, timedelta
from aiohttp import ClientSession
from urllib.parse import urlparse
import aiohttp
from tortoise.expressions import Q
import logging
import re
import numpy as np
from pprint import pprint
from functools import lru_cache
# from fastapi_cache.decorator import cache
from scholarship_tests.models import ScholarshipTestSeries, ScholarshipTestSeries_Pydantic
import json
import uuid
from slugify import slugify
from datetime import datetime, date
from operator import itemgetter
from typing import List, Optional
import pytz
from botocore.client import BaseClient
from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from pydantic import BaseModel, validator
from starlette.responses import JSONResponse
from tortoise.contrib.fastapi import HTTPNotFoundError
from dateutil.relativedelta import relativedelta
from admin_dashboard.controller import upload_images
from admin_dashboard.models import CategoryTopics, CategoryTopics_Pydantic, Coupons, Preference, Course, \
    Preference_Pydantic, Course_Pydantic, \
    CourseSubscriptionPlans_Pydantic, CourseSubscriptionPlans, CourseCategories, \
    CourseCategories_Pydantic, Category, CourseCategoryTestSeries, CourseCategoryLectures, CourseCategoryNotes, \
    LiveClasses, InstructorIn_Pydantic, Instructor, Instructor_Pydantic, LiveClasses_Pydantic, \
    addAppStaticUrls, Topics, \
    addAppStaticUrls_Pydantic, offerBanners, offerBanners_Pydantic, Scholarship2021, InterViewProgram, CourseCategoryLecturesVideoURLS
from aws_services.deps import s3_auth
from student.models import Student, StudentIn_Pydantic
from student_choices.models import StudentChoices, activeSubscription, \
    BookMarkedVideos, BookMarkedNotes, BookMarkedTestseries, studentActivity, studentNotesActivity, \
    studentTestSeriesActivity, studentVideoActivity
from study_material.models import StudyMaterialOrderInstance, TestSeriesOrders
from utils.util import get_current_user
from .pydantic_models import CategoriesPydantic, CourseCategoriesCount, CourseCategoryPydantic, CoursePydantic, CourseSubscriptionPlans_course
from scholarship_tests.models import StudentScholarshipTestSeriesRecord
import pytz
from configs import appinfo

tz = pytz.timezone('Asia/Kolkata')
updated_at = datetime.now(tz)


def get_session():
    return True


def is_database_online(session: bool = Depends(get_session)):
    return session


router = APIRouter()


class Status(BaseModel):
    message: str


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()
cache_time = settings.cache_time


@router.get('/get_all_preferences/', response_model=List[Preference_Pydantic],
            responses={404: {"model": HTTPNotFoundError}})
# @cache(expire=3600)
async def get_all_preferences(current_user: Preference_Pydantic = Depends(get_current_user)):
    try:
        obj = await Preference_Pydantic.from_queryset(Preference.all().order_by('display_order') )
        return jsonable_encoder(obj)
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/get_each_preference_courses/{preference_slug}', response_model=Preference_Pydantic,
            responses={404: {"model": HTTPNotFoundError}})
async def get_each_preference_courses(preference_slug: str,
                                      _=Depends(get_current_user)):
    try:
        return await Preference_Pydantic.from_queryset_single(Preference.get(slug=preference_slug)
    )
        
        # Fetch the Preference
        preference = await Preference.get(slug=preference_slug)

        # Fetch and sort related courses
        courses = await Course.filter(preference_id=preference.id).order_by('name').all()

        # Combine data (manually map courses to preference if necessary)
        preference_data = await Preference_Pydantic.from_tortoise_orm(preference)
        preference_data.courses = courses  # Assuming you have a structure to hold this

        return preference_data

    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)

# @router.post('/Course_Category', response_model=Category_Pydantic)
# async def create_course_category(todo: CategoryIn_Pydantic):
#     obj = await CourseCategories.create(**todo.dict(exclude_unset=True))
#     return await Category_Pydantic.from_tortoise_orm(obj)


@router.post('/course_details/{c_slug}/', response_model=List[CategoriesPydantic])
async def course_details(c_slug: str, _=Depends(get_current_user), ):
    try:
        # course = await Course.get(slug=c_slug)
        course_cat_obj = await CourseCategories_Pydantic.from_queryset(
            CourseCategories.filter(course__slug=c_slug).order_by('category__created_at'))
        return course_cat_obj
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/course_details1/{c_slug}/', response_model=List[CourseCategoriesCount])
async def course_details(c_slug: str, _=Depends(get_current_user), ):
    try:
        course_cat_obj = await CourseCategories_Pydantic.from_queryset(
            CourseCategories.filter(course__slug=c_slug))

        new_arr = []

        for category in course_cat_obj:
            cat_id = category.category.id
            lecture_count = await CourseCategoryLectures.filter(
                category_topic__category__course__slug=c_slug, category_topic__category__category__id=cat_id
            ).count()

            notes_count = await CourseCategoryNotes.filter(
                category_topic__category__course__slug=c_slug, category_topic__category__category__id=cat_id
            ).count()

            test_series_count = await CourseCategoryTestSeries.filter(
                category_topic__category__course__slug=c_slug, category_topic__category__category__id=cat_id
            ).count()
            new_dict = category.dict()
            new_dict.update({'lectures': lecture_count})
            new_dict.update({'notes': notes_count})
            new_dict.update({'test_series': test_series_count})

            new_arr.append(new_dict)

        return new_arr
    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)

'''API UNDER TEST'''


# Utility function to get the size of a video given its URL

async def get_video_size(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            if response.status == 200:
                return int(response.headers.get('Content-Length', 0))
            else:
                return None

# Utility function to extract video ID from URL


def extract_video_id(url: str) -> str:
    # Use regular expression to match the video ID in the URL
    match = re.search(r'([a-f0-9\-]{36})', url)
    return match.group(1) if match else None


# Utility function to extract the base URL


def extract_base_url(url):
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"


# Utility function to update video URLs

def is_multiple_of_100(n):
    return n % 10 == 0


async def update_video_urls():
    # Fetch rows where mobile_video_url contains the specific string, reducing the number of rows fetched.
    query = Q(mobile_video_url__contains=".b-cdn.net/")
    # query = Q(video_360__contains=".b-cdn.net/")
    # Add condition to check that video_360 is not null
    # query &= Q(video_size_360__isnull=True)
    # query = Q(video_size_360__isnull=True)
    # Calculate the date 30 days ago from today
    date_30_days_ago = datetime.today() - timedelta(days=30)

    # lectures = await CourseCategoryLectures.filter(query, created_at__gte=date_30_days_ago)
    lectures = await CourseCategoryLectures.filter(query)
    # print(f"No. of lectures: {lectures}")

    # lectures = await CourseCategoryLectures.all()

    i = 1
    # for lecture in lectures:
    #     lecture.mobile_video_url = None
    #     await lecture.save()
    #     print(f'done:{i}')
    #     i = i + 1
    # return True
    # List to hold objects that need to be updated
    lectures_to_update = []

    # Iterate over each filtered row
    i = 0
    j = 100
    for lecture in lectures:
        # video_id = extract_video_id(lecture.mobile_video_url)
        # video_id = extract_video_id(lecture.video_360)

        # print(video_id)

        # return True

        lecture.video_360 = None
        lecture.video_540 = None

            # if video_size_360 is not None:
            #     lecture.video_size_360 = video_size_360
            # if video_size_480 is not None:
            #     lecture.video_size_540 = video_size_480

            # Append object to the list
        lectures_to_update.append(lecture)
        print(f'done:{i}')
        i = i + 1

        # If video ID is found, construct the new URLs
        # if video_id:

            # base_url = extract_base_url(lecture.mobile_video_url)
            # base_url = extract_base_url(lecture.video_360)
            # new_video_360 = f"{base_url}/{video_id}/play_360p.mp4"
            # new_video_480 = f"{base_url}/{video_id}/play_480p.mp4"

            # m3u8_url = f"{base_url}/{video_id}/playlist.m3u8"

            # Get video sizes
            # video_size_360 = await get_video_size(new_video_360)
            # video_size_480 = await get_video_size(new_video_480)

            # print(i)
            # print(f"video_size_360++{video_size_360}")
            # print(f"video_size_480++{video_size_480}")

            # Update fields in the object
            # lecture.video_360 = new_video_360
            # lecture.video_540 = new_video_480
            # lecture.video_360 = None
            # lecture.video_540 = None
            # lecture.mobile_video_url = m3u8_url
            # lecture.mobile_video_url = None
            # lecture.video_size_360 = None
            # lecture.video_size_540 = None

            # # if video_size_360 is not None:
            # #     lecture.video_size_360 = video_size_360
            # # if video_size_480 is not None:
            # #     lecture.video_size_540 = video_size_480

            # # Append object to the list
            # lectures_to_update.append(lecture)
            # print(f'done:{i}')
            # i = i + 1
    # await CourseCategoryLectures.bulk_update(lectures_to_update, fields=["video_360", "video_540", "mobile_video_url", "video_size_360", "video_size_540"])
    await CourseCategoryLectures.bulk_update(lectures_to_update, fields=["video_360", "video_540"])

    # if is_multiple_of_100(i):
    #     # await CourseCategoryLectures.bulk_update(lectures_to_update, fields=["video_360", "video_540", "video_size_360", "video_size_540"])
    #     lectures_to_update = []
    #     i = i+1

    # print(lectures_to_update)
    # Perform bulk update
    # if lectures_to_update:
    #     await CourseCategoryLectures.bulk_update(lectures_to_update, fields=["video_360", "video_540", "video_size_360", "video_size_540"])


async def getBookMarkedVideos(student_id):
    if await BookMarkedVideos.exists(
            student__id=student_id):
        video_ids = await BookMarkedVideos.filter(
            student__id=student_id).values('video__id')
        video_list = list(map(lambda x: x['video__id'], video_ids))
        new_list = list(filter(None, video_list))

        return new_list
    else:
        return None


async def getBookMarkedNotes(student_id):
    if await BookMarkedNotes.exists(
            student__id=student_id):
        notes_ids = await BookMarkedNotes.filter(
            student__id=student_id).values('notes__id')
        notes_list = list(map(lambda x: x['notes__id'], notes_ids))
        new_list = list(filter(None, notes_list))

        return new_list
    else:
        return None


@router.post('/update_video_links')
async def update_video_links(_=Depends(get_current_user)):
    await update_video_urls()
    # logging.basicConfig(level=logging.DEBUG)

    return {"status": "Video links updated"}


@router.post('/course_category/{course_slug}/{category_slug}/{student_id}/',
             #  response_model=CourseCategoryPydantic
             )
async def get_course_category(course_slug: str, category_slug: str, student_id: str, _=Depends(get_current_user)):
    total_length_of_lectures = await CourseCategoryLectures.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug).count()
    total_length_of_notes = await CourseCategoryNotes.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug).count()
    total_length_of_test_series = await CourseCategoryTestSeries.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug).count()

    async def execute_lectures_loop(subscription_initial_video_counter):

        topics = await CourseCategoryLectures.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug).group_by("category_topic__topic__id", "category_topic__order_seq").order_by("category_topic__order_seq").values(topic_id="category_topic__topic__id")
        topics = np.array(topics)
        lectures = []

        for topic in topics:
            allowed_lectures = []
            topic_obj = await Topics.get(id=topic["topic_id"]).values("id", "name", "slug")

            lectures_obj = await CourseCategoryLectures.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug, category_topic__topic__id=topic["topic_id"]).order_by("order_display").\
                values("id", "title", "slug", "discription", "web_video_url", "app_thumbnail", "video_duration", "mobile_video_url",
                       "video_id", "video_360", "video_540", "video_720", "video_size_360", "video_size_540", "video_size_720")
            #  prefetch_related("video_studentVideoActivity","students_bookmarked_video","CourseCategoryLecturesVideoURLS")

            # lectures_obj = np.array(lectures_obj) order_by("order_display").

            each_topic_lectures_length = len(lectures_obj)

            if subscription_initial_video_counter <= each_topic_lectures_length:
                print(
                    "LECTURES:subscription_initial_video_counter <= each_topic_lectures_length")
                for i in range(subscription_initial_video_counter):
                    allowed_lectures.append(lectures_obj[i])

                not_allowed_lectures_length = each_topic_lectures_length - \
                    subscription_initial_video_counter

                for j in range(not_allowed_lectures_length):
                    disallowed_dict = lectures_obj[subscription_initial_video_counter + j]
                    disallowed_dict.update({"mobile_video_url": None})
                    disallowed_dict.update({"web_video_url": None})
                    disallowed_dict.update({"video_id": None})
                    disallowed_dict.update({"video_360": None})
                    disallowed_dict.update({"video_540": None})
                    disallowed_dict.update({"video_720": None})
                    disallowed_dict.update({"video_size_360": None})
                    disallowed_dict.update({"video_size_540": None})
                    disallowed_dict.update({"video_size_720": None})
                    allowed_lectures.append(disallowed_dict)
                subscription_initial_video_counter = 0
            else:
                print(
                    "LECTURES:subscription_initial_video_counter > each_topic_lectures_length")

                allowed_lectures = lectures_obj

                subscription_initial_video_counter = subscription_initial_video_counter - \
                    each_topic_lectures_length

            lectures.append(
                {"topic": topic_obj, "CategoryLectures": allowed_lectures})
        return lectures

    async def execute_notes_loop(initial_notes_counter):
        topics = await CourseCategoryNotes.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug).group_by("category_topic__topic__id").values(topic_id="category_topic__topic__id")
        topics = np.array(topics)
        notes = []
        for topic in topics:
            allowed_notes = []
            topic_obj = await Topics.get(id=topic["topic_id"]).values("id", "name", "slug")

            notes_obj = await CourseCategoryNotes.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug, category_topic__topic__id=topic["topic_id"]).\
                prefetch_related("notes_studentNotesActivity",
                                 "students_bookmarked_notes").values("id", "title", "slug", "thumbnail", "notes_url")

            each_topic_notes_length = len(notes_obj)

            if each_topic_notes_length <= total_length_of_notes:
                if initial_notes_counter <= each_topic_notes_length:
                    for i in range(initial_notes_counter):
                        allowed_notes.append(notes_obj[i])

                    not_allowed_notes_length = each_topic_notes_length - initial_notes_counter

                    for j in range(not_allowed_notes_length):
                        disallowed_dict = notes_obj[initial_notes_counter + j]
                        disallowed_dict.update({"notes_url": None})
                        allowed_notes.append(disallowed_dict)
                    initial_notes_counter = 0
                else:
                    allowed_notes = notes_obj

                    initial_notes_counter = initial_notes_counter - each_topic_notes_length

            notes.append({"topic": topic_obj, "CategoryNotes": allowed_notes})

        return notes

    async def execute_test_series_loop(subscription_test_series_counter):
        topics = await CourseCategoryTestSeries.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug).group_by("category_topic__topic__id").values(topic_id="category_topic__topic__id")
        topics = np.array(topics)
        test_series = []
        for topic in topics:
            allowed_test_series = []
            topic_obj = await Topics.get(id=topic["topic_id"]).values("id", "name", "slug")

            test_series_obj = await CourseCategoryTestSeries.filter(category_topic__category__course__slug=course_slug, category_topic__category__category__slug=category_slug, category_topic__topic__id=topic["topic_id"]).\
                prefetch_related("test_series_studentTestSeriesActivity",
                                 "students_bookmarked_testseries").values("id", "title", "thumbnail", "no_of_qstns", "time_duration", "marks", "description")

            each_topic_test_series_length = len(test_series_obj)

            print(test_series_obj)
            if subscription_test_series_counter <= each_topic_test_series_length:
                print(
                    "TestSeries:subscription_test_series_counter <= each_topic_lectures_length")

                for i in range(subscription_test_series_counter):
                    test_series_obj[i].update({"isBookmarked": False})
                    allowed_test_series.append(test_series_obj[i])

                not_allowed_test_series_length = each_topic_test_series_length - \
                    subscription_test_series_counter

                for j in range(not_allowed_test_series_length):
                    disallowed_dict = test_series_obj[subscription_test_series_counter + j]
                    disallowed_dict.update({"id": None})
                    disallowed_dict.update({"attempted": False})
                    disallowed_dict.update({"isBookmarked": False})
                    allowed_test_series.append(disallowed_dict)
                subscription_test_series_counter = 0
            else:
                print(
                    "TestSeries:subscription_test_series_counter > each_topic_lectures_length")

                add_bookmark = []
                for x in test_series_obj:
                    x.update({"isBookmarked": False})
                    add_bookmark.append(x)
                allowed_test_series = add_bookmark

                subscription_test_series_counter = subscription_test_series_counter - \
                    each_topic_test_series_length

            test_series.append(
                {"topic": topic_obj, "CategoryTestSeries": allowed_test_series})
        return test_series

    category_course_ins = await CourseCategories.get(course__slug=course_slug, category__slug=category_slug)

    now = datetime.now(tz)

    if not category_course_ins.is_free:

        if await activeSubscription.exists(student__id=student_id, course__slug=course_slug):

            active_subscription = await activeSubscription.get(student__id=student_id, course__slug=course_slug).values(
                "subscription__id")

            subscription_id = active_subscription["subscription__id"]
            if await StudentChoices.exists(student__id=student_id,
                                           subscription__id=subscription_id, expiry_date__gte=now, payment__payment_status=2):
                student_choice = await activeSubscription.get(student__id=student_id, course__slug=course_slug) \
                    .values("subscription__no_of_videos", "subscription__no_of_notes",
                            "subscription__no_of_tests", "subscription__live_classes_access")

                no_of_videos = student_choice["subscription__no_of_videos"]
                no_of_notes = student_choice["subscription__no_of_notes"]
                no_of_tests = student_choice["subscription__no_of_tests"]
                live_classes_access = student_choice["subscription__live_classes_access"]

                subscription_initial_video_counter = no_of_videos
                subscription_initial_notes_counter = no_of_notes
                subscription_initial_test_series_counter = no_of_tests

                updated_access_lect_array = await execute_lectures_loop(
                    subscription_initial_video_counter)

                updated_access_notes_array = await execute_notes_loop(
                    subscription_initial_notes_counter)
                print("==================Notes here ==========")
                print(updated_access_notes_array)
                updated_access_test_series_array = await execute_test_series_loop(
                    subscription_initial_test_series_counter)

                result = {
                    "Lectures": updated_access_lect_array,
                    "Notes": updated_access_notes_array,
                    "TestSeries": updated_access_test_series_array,
                }

                return result
            else:
                '''Free content free tier'''

                initial_video_counter = 2
                initial_notes_counter = 2
                initial_test_series_counter = 2

                updated_access_lect_array = await execute_lectures_loop(
                    initial_video_counter)

                updated_access_notes_array = await execute_notes_loop(
                    initial_notes_counter)

                updated_access_test_series_array = await execute_test_series_loop(
                    initial_test_series_counter)

                result = {
                    "Lectures": updated_access_lect_array,
                    "Notes": updated_access_notes_array,
                    "TestSeries": updated_access_test_series_array,
                }
                return result

        else:
            print("FREE CONTENT EXECUTED")
            '''Free content free tier'''

            initial_video_counter = 2
            initial_notes_counter = 2
            initial_test_series_counter = 2

            updated_access_lect_array = await execute_lectures_loop(
                initial_video_counter)

            updated_access_notes_array = await execute_notes_loop(
                initial_notes_counter)

            updated_access_test_series_array = await execute_test_series_loop(
                initial_test_series_counter)

            result = {
                "Lectures": updated_access_lect_array,
                "Notes": updated_access_notes_array,
                "TestSeries": updated_access_test_series_array,
            }
            return result

    else:
        print('IT IS FREE===========================')
        initial_video_counter = total_length_of_lectures
        initial_notes_counter = total_length_of_notes
        initial_test_series_counter = total_length_of_test_series

        updated_access_lect_array = await execute_lectures_loop(
            initial_video_counter)

        updated_access_notes_array = await execute_notes_loop(
            initial_notes_counter)

        updated_access_test_series_array = await execute_test_series_loop(
            initial_test_series_counter)

        result = {
            "Lectures": updated_access_lect_array,
            "Notes": updated_access_notes_array,
            "TestSeries": updated_access_test_series_array,
        }

    return result


@router.post('/v1/course_category/{course_slug}/{category_slug}/{student_id}/',
             #  response_model=CourseCategoryPydantic
             )
# @cache(expire=cache_time)
async def course_category(course_slug: str, category_slug: str, student_id: str, _=Depends(get_current_user)):
    try:
        global updated_access_lect_array, updated_access_notes_array, updated_access_test_series_array, result

        if await Student.exists(id=student_id):

            book_marked_videos = await getBookMarkedVideos(student_id)

            async def check_isBookmarkedNotes(notes_id):

                if await BookMarkedNotes.exists(
                        student__id=student_id, notes__id=notes_id):
                    return True

                else:
                    return False

            async def check_isBookmarkedTestSeries(series_id):

                if await BookMarkedTestseries.exists(
                        student__id=student_id, test_series__id=series_id):
                    return True
                else:
                    return False

            async def check_isLikedVideo(video_id):
                return False

            async def watch_activity(video_id):
                if await studentActivity.exists(
                        student__id=student_id, course__slug=course_slug):

                    if await studentVideoActivity.exists(student_activity__student__id=student_id, student_activity__course__slug=course_slug, video_id__id=video_id):
                        activity_instance = await studentVideoActivity.filter(student_activity__student__id=student_id, student_activity__course__slug=course_slug,
                                                                              video_id__id=video_id).values("watch_time")
                        watch_time = activity_instance[0]["watch_time"]
                    else:
                        watch_time = None
                else:
                    watch_time = None
                return watch_time

            async def notes_activity(note_id):
                if await studentActivity.exists(
                        student__id=student_id, course__slug=course_slug):

                    activity_instance = await studentActivity.get(student_activity__student__id=student_id, student_activity__course__slug=course_slug, )
                    notes_instance = await CourseCategoryNotes.get(id=note_id)
                    if await studentNotesActivity.exists(student_activity__student__id=student_id, student_activity__course__slug=course_slug, note_id__id=note_id):
                        notes_activity_instance = await studentNotesActivity.get(student_activity=activity_instance,
                                                                                 note_id__id=note_id)
                        last_seen = notes_activity_instance.last_seen
                    else:
                        last_seen = None
                else:
                    last_seen = None
                return last_seen

            async def testseries_activity(testseries_id):
                if await studentActivity.exists(
                        student__id=student_id, course__slug=course_slug):
                    if await studentTestSeriesActivity.exists(student_activity__student__id=student_id, student_activity__course__slug=course_slug,
                                                              test_series_id__id=testseries_id):
                        attempted = True
                    else:
                        attempted = False
                else:
                    attempted = False
                return attempted

            obj = await CourseCategories.exists(course__slug=course_slug,
                                                category__slug=category_slug)

            if obj:

                course_cat_obj = await CategoryTopics.filter(category__course__slug=course_slug,
                                                             category__category__slug=category_slug).order_by('order_seq')
                # return course_cat_obj
                resp = jsonable_encoder(course_cat_obj)
                access_lectures_counter = 0

                total_length_of_lectures = await CourseCategoryLectures.filter(
                    category_topic__category__course__slug=course_slug,
                    category_topic__category__category__slug=category_slug).count()

                total_length_of_notes = await CourseCategoryNotes.filter(
                    category_topic__category__course__slug=course_slug,
                    category_topic__category__category__slug=category_slug).count()

                total_length_of_test_series = await CourseCategoryTestSeries.filter(
                    category_topic__category__course__slug=course_slug,
                    category_topic__category__category__slug=category_slug).count()
                # return {total_length_of_test_series}

                async def execute_lectures_loop(array, subscription_video_counter):
                    print('=====LECTURE LOOP=====')
                    forward_access_flag = 1
                    category_topics_array = []
                    for category_topics_obj in array:

                        access_lectures = []

                        if total_length_of_lectures > subscription_video_counter:
                            print(
                                "total_length_of_lectures > subscription_video_counter")
                            new_lect_dict = {"topic": await Topics.get(id=category_topics_obj.topic_id)
                                             }
                            # return new_lect_dict
                            if len(category_topics_obj.CategoryLectures) > subscription_video_counter:
                                access_counter = subscription_video_counter
                                print("access_counter_here: " +
                                      str(access_counter))
                                """Old code """
                                if category_topics_obj.CategoryLectures:

                                    if forward_access_flag:
                                        for i in range(access_counter):
                                            print(
                                                "category lectures greater than subscription videos")
                                            new_dict = category_topics_obj.CategoryLectures[i].dict(
                                            )

                                            video_id = category_topics_obj.CategoryLectures[i].id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            watch_time = await watch_activity(video_id)
                                            new_dict.update(
                                                {"watch_time": watch_time})
                                            access_lectures.append(new_dict)

                                        remaining_counter = len(
                                            category_topics_obj.CategoryLectures) - access_counter
                                        for j in range(remaining_counter):
                                            updated_dict = category_topics_obj.CategoryLectures[access_counter + j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)
                                    else:
                                        for j in range(len(category_topics_obj.CategoryLectures)):
                                            updated_dict = category_topics_obj.CategoryLectures[j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)

                                    sorted_list = sorted(
                                        access_lectures, key=itemgetter('order_display'))
                                    new_lect_dict.update(
                                        {"CategoryLectures": sorted_list})
                                    category_topics_array.append(new_lect_dict)
                                    forward_access_flag = 0

                            elif len(category_topics_obj.CategoryLectures) == subscription_video_counter:
                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    if forward_access_flag:
                                        for eachLecture in category_topics_obj.CategoryLectures:
                                            new_dict = eachLecture.dict()
                                            video_id = eachLecture.id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            watch_time = await watch_activity(video_id)
                                            new_dict.update(
                                                {"watch_time": watch_time})
                                            access_lectures.append(new_dict)

                                    else:
                                        for j in range(len(category_topics_obj.CategoryLectures)):
                                            updated_dict = category_topics_obj.CategoryLectures[j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)

                                    sorted_list = sorted(
                                        access_lectures, key=itemgetter('order_display'))
                                    new_lect_dict.update(
                                        {"CategoryLectures": sorted_list})

                                    category_topics_array.append(new_lect_dict)
                                    forward_access_flag = 0
                                    subscription_video_counter = 0
                                    print("Both are equal")

                            elif (len(category_topics_obj.CategoryLectures) < subscription_video_counter):

                                """ check for is bookmarked"""
                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    if forward_access_flag:
                                        for eachLecture in category_topics_obj.CategoryLectures:
                                            new_dict = eachLecture.dict()
                                            video_id = eachLecture.id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            watch_time = await watch_activity(video_id)
                                            new_dict.update(
                                                {"watch_time": watch_time})
                                            access_lectures.append(new_dict)
                                            print(
                                                "lectures are less than subscription")
                                    else:
                                        for j in range(len(category_topics_obj.CategoryLectures)):
                                            updated_dict = category_topics_obj.CategoryLectures[j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)

                                    # access_lectures.append(new_lectures)

                                    subscription_video_counter -= len(
                                        category_topics_obj.CategoryLectures)
                                    sorted_list = sorted(
                                        access_lectures, key=itemgetter('order_display'))
                                    new_lect_dict.update(
                                        {"CategoryLectures": sorted_list})
                                    category_topics_array.append(new_lect_dict)

                                # return category_topics_array

                        elif total_length_of_lectures <= subscription_video_counter:
                            print(
                                "total_length_of_lectures <= subscription_video_counter")

                            new_lect_dict = {"topic": await Topics.get(id=category_topics_obj['topic_id']).values("id", "name", "slug")}

                            # category_topics_array.append(
                            #     )

                            new_lectures = []
                            if await CourseCategoryLectures.exists(
                                    category_topic__id=category_topics_obj['id']):
                                CategoryLectures = await CourseCategoryLectures.filter(
                                    category_topic__id=category_topics_obj['id'])
                                for eachLecture in CategoryLectures:
                                    new_dict = jsonable_encoder(eachLecture)
                                    video_id = eachLecture.id
                                    print("waiting....")
                                    print("Video id here:", video_id)
                                    if book_marked_videos:
                                        if video_id in book_marked_videos:

                                            is_bookmarked = True
                                        else:
                                            is_bookmarked = False
                                    else:
                                        is_bookmarked = False
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    # is_liked = await check_isLikedVideo(video_id)
                                    # new_dict.update({"isLiked": is_liked})
                                    # watch_time = await watch_activity(video_id)
                                    # new_dict.update({"watch_time": watch_time})

                                    access_lectures.append(new_dict)

                                # access_lectures.append(new_lectures)

                                sorted_list = sorted(
                                    access_lectures, key=itemgetter('order_display'))
                                new_lect_dict.update(
                                    {"CategoryLectures": sorted_list})

                                category_topics_array.append(new_lect_dict)
                            # category_topics_array.append({"CategoryLectures": access_lectures})

                    return category_topics_array

                async def execute_notes_loop(array, subscription_notes_counter):
                    print("=====NOTES LOOP=======")
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

                async def execute_test_series_loop(array, subscription_series_counter):
                    print("=============TEST SERIES LOOP========")
                    category_topics_array = []

                    for category_topics_obj in array:
                        access_series = []

                        if total_length_of_test_series > subscription_series_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                "category"})}

                            if len(category_topics_obj.CategoryTestSeries) > subscription_series_counter:
                                for i in range(subscription_series_counter):
                                    new_dict = category_topics_obj.CategoryTestSeries[i].dict(
                                        exclude={'CategoryTestSeriesQuestions'})
                                    test_series_id = category_topics_obj.CategoryTestSeries[i].id
                                    is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    attempted = await testseries_activity(test_series_id)
                                    new_dict.update({"attempted": attempted})
                                    access_series.append(new_dict)
                                remaining_counter = len(
                                    category_topics_obj.CategoryTestSeries) - subscription_series_counter
                                for j in range(remaining_counter):
                                    updated_dict = category_topics_obj.CategoryTestSeries[
                                        subscription_series_counter + j].dict(exclude={'CategoryTestSeriesQuestions'})
                                    test_series_id = category_topics_obj.CategoryTestSeries[
                                        subscription_series_counter + j].id
                                    is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                    updated_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    attempted = await testseries_activity(test_series_id)
                                    updated_dict.update(
                                        {"attempted": attempted})
                                    access_series.append(updated_dict)

                                new_lect_dict.update(
                                    {"CategoryTestSeries": access_series})
                                category_topics_array.append(new_lect_dict)
                                # subscription_series_counter = 0

                            if subscription_series_counter and (
                                    len(category_topics_obj.CategoryTestSeries) < subscription_series_counter
                            ):
                                if category_topics_obj.CategoryTestSeries:
                                    for eachTest in category_topics_obj.CategoryTestSeries:
                                        new_dict = eachTest.dict(
                                            exclude={'CategoryTestSeriesQuestions'})
                                        test_series_id = eachTest.id
                                        is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        attempted = await testseries_activity(test_series_id)
                                        new_dict.update(
                                            {"attempted": attempted})

                                        access_series.append(new_dict)
                                    # subscription_series_counter -= len(category_topics_obj.CategoryTestSeries)
                                    new_lect_dict.update(
                                        {"CategoryTestSeries": access_series})

                                    category_topics_array.append(new_lect_dict)

                            if len(category_topics_obj.CategoryTestSeries) == subscription_series_counter:
                                if category_topics_obj.CategoryTestSeries:
                                    for eachTest in category_topics_obj.CategoryTestSeries:
                                        new_dict = eachTest.dict(
                                            exclude={'CategoryTestSeriesQuestions'})
                                        test_series_id = eachTest.id
                                        is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        attempted = await testseries_activity(test_series_id)
                                        new_dict.update(
                                            {"attempted": attempted})
                                        access_series.append(new_dict)
                                        # subscription_series_counter = 0

                                    new_lect_dict.update(
                                        {"CategoryTestSeries": access_series})

                                    category_topics_array.append(new_lect_dict)
                                return category_topics_array

                                # return category_topics_array

                        elif total_length_of_test_series <= subscription_series_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                "category"})}
                            if category_topics_obj.CategoryTestSeries:
                                for eachTest in category_topics_obj.CategoryTestSeries:
                                    new_dict = eachTest.dict(
                                        exclude={'CategoryTestSeriesQuestions'})
                                    test_series_id = eachTest.id
                                    is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    attempted = await testseries_activity(test_series_id)
                                    new_dict.update({"attempted": attempted})
                                    access_series.append(new_dict)
                                new_lect_dict.update(
                                    {"CategoryTestSeries": access_series})

                                category_topics_array.append(new_lect_dict)

                    return category_topics_array

                category_course_ins = await CourseCategories.get(course__slug=course_slug, category__slug=category_slug)

                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz)

                if not category_course_ins.is_free:
                    if await activeSubscription.exists(student__id=student_id, course__slug=course_slug):

                        active_subscription = await activeSubscription.get(student__id=student_id, course__slug=course_slug).values(
                            "subscription__id")

                        subscription_id = active_subscription["subscription__id"]
                        if await StudentChoices.exists(student__id=student_id,
                                                       subscription__id=subscription_id, expiry_date__gte=now, payment__payment_status=2):
                            student_choice = await activeSubscription.get(student__id=student_id, course__slug=course_slug) \
                                .values("subscription__no_of_videos", "subscription__no_of_notes",
                                        "subscription__no_of_tests", "subscription__live_classes_access")

                            no_of_videos = student_choice["subscription__no_of_videos"]
                            no_of_notes = student_choice["subscription__no_of_notes"]
                            no_of_tests = student_choice["subscription__no_of_tests"]
                            live_classes_access = student_choice["subscription__live_classes_access"]

                            subscription_initial_video_counter = no_of_videos
                            subscription_initial_notes_counter = no_of_notes
                            subscription_initial_test_series_counter = no_of_tests

                            updated_access_lect_array = await execute_lectures_loop(
                                resp, subscription_initial_video_counter)

                            # updated_access_notes_array = await execute_notes_loop(
                            #     resp, subscription_initial_notes_counter)

                            # updated_access_test_series_array = await execute_test_series_loop(
                            #     resp, subscription_initial_test_series_counter)

                            result = {
                                "Lectures": updated_access_lect_array,
                                # "Notes": updated_access_notes_array,
                                # "TestSeries": updated_access_test_series_array,
                            }

                            return result
                        else:
                            '''Free content free tier'''

                            initial_video_counter = 2
                            initial_notes_counter = 2
                            initial_test_series_counter = 2

                            updated_access_lect_array = await execute_lectures_loop(
                                resp, initial_video_counter)

                            # updated_access_notes_array = await execute_notes_loop(
                            #     resp, initial_notes_counter)

                            # updated_access_test_series_array = await execute_test_series_loop(
                            #     resp, initial_test_series_counter)

                            result = {
                                "Lectures": updated_access_lect_array,
                                # "Notes": updated_access_notes_array,
                                # "TestSeries": updated_access_test_series_array,
                            }
                            return result

                    else:
                        print("FREE CONTENT EXECUTED")
                        '''Free content free tier'''

                        initial_video_counter = 2
                        initial_notes_counter = 2
                        initial_test_series_counter = 2

                        updated_access_lect_array = await execute_lectures_loop(
                            resp, initial_video_counter)

                        # updated_access_notes_array = await execute_notes_loop(
                        #     resp, initial_notes_counter)

                        # updated_access_test_series_array = await execute_test_series_loop(
                        #     resp, initial_test_series_counter)

                        result = {
                            "Lectures": updated_access_lect_array,
                            # "Notes": updated_access_notes_array,
                            # "TestSeries": updated_access_test_series_array,
                        }
                        return result

                else:
                    initial_video_counter = total_length_of_lectures
                    initial_notes_counter = total_length_of_notes
                    initial_test_series_counter = total_length_of_test_series

                    updated_access_lect_array = await execute_lectures_loop(
                        resp, initial_video_counter)

                    # updated_access_notes_array = await execute_notes_loop(
                    #     resp, initial_notes_counter)

                    # updated_access_test_series_array = await execute_test_series_loop(
                    #     resp, initial_test_series_counter)

                    result = {
                        "Lectures": updated_access_lect_array,
                        "Notes": updated_access_notes_array,
                        "TestSeries": updated_access_test_series_array,
                    }

                    return result

    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.post('/v0/course_category/{course_slug}/{category_slug}/{student_id}/',
             response_model=CourseCategoryPydantic
             )
# @cache(expire=cache_time)
async def course_category(course_slug: str, category_slug: str, student_id: str, _=Depends(get_current_user)):
    try:
        global updated_access_lect_array, updated_access_notes_array, updated_access_test_series_array, result
        course = await Course.get(slug=course_slug)
        category = await Category.get(slug=category_slug)
        if await Student.exists(id=student_id):
            student_instance = await Student.get(id=student_id)

            async def check_isBookmarkedVideo(video_id):
                video_instance = await CourseCategoryLectures.get(id=video_id)
                if await BookMarkedVideos.exists(
                        student=student_instance, video=video_instance):
                    return True

                else:
                    return False

            async def check_isBookmarkedNotes(notes_id):
                notes_instance = await CourseCategoryNotes.get(id=notes_id)
                if await BookMarkedNotes.exists(
                        student=student_instance, notes=notes_instance):
                    return True

                else:
                    return False

            async def check_isBookmarkedTestSeries(series_id):
                series_instance = await CourseCategoryTestSeries.get(id=series_id)
                if await BookMarkedTestseries.exists(
                        student=student_instance, test_series=series_instance):
                    return True
                else:
                    return False

            async def check_isLikedVideo(video_id):
                return False

            async def watch_activity(video_id):
                if await studentActivity.exists(
                        student=student_instance, course=course):

                    videoActivity_instance = await studentActivity.get(student=student_instance, course=course)
                    video_instance = await CourseCategoryLectures.get(id=video_id)
                    if await studentVideoActivity.exists(student_activity=videoActivity_instance, video_id=video_instance):
                        activity_instance = await studentVideoActivity.filter(student_activity=videoActivity_instance,
                                                                              video_id=video_instance).values("watch_time")
                        watch_time = activity_instance[0]["watch_time"]
                    else:
                        watch_time = None
                else:
                    watch_time = None
                return watch_time

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

            async def testseries_activity(testseries_id):
                if await studentActivity.exists(
                        student=student_instance, course=course):

                    activity_instance = await studentActivity.get(student=student_instance, course=course)
                    testseries_instance = await CourseCategoryTestSeries.get(id=testseries_id)
                    if await studentTestSeriesActivity.exists(student_activity=activity_instance,
                                                              test_series_id=testseries_instance):
                        attempted = True
                    else:
                        attempted = False
                else:
                    attempted = False
                return attempted

            obj = await CourseCategories.exists(course=course,
                                                category=category)

            if obj:

                course_cat_obj = await CategoryTopics_Pydantic.from_queryset(
                    CategoryTopics.filter(category__course__slug=course_slug,
                                          category__category__slug=category_slug).order_by('order_seq'))

                resp = course_cat_obj
                access_lectures_counter = 0
                total_length_of_lectures = 0
                total_length_of_notes = 0
                total_length_of_test_series = 0

                for category_topics in resp:
                    total_length_of_lectures += len(
                        category_topics.CategoryLectures)
                    total_length_of_notes += len(category_topics.CategoryNotes)
                    total_length_of_test_series += len(
                        category_topics.CategoryTestSeries)

                async def execute_lectures_loop(array, subscription_video_counter):
                    forward_access_flag = 1
                    category_topics_array = []
                    for category_topics_obj in array:

                        access_lectures = []

                        if total_length_of_lectures > subscription_video_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                                                                     "category"})}

                            if len(category_topics_obj.CategoryLectures) > subscription_video_counter:
                                access_counter = subscription_video_counter
                                print("access_counter_here: " +
                                      str(access_counter))
                                """Old code """
                                if category_topics_obj.CategoryLectures:

                                    if forward_access_flag:
                                        for i in range(access_counter):
                                            print(
                                                "category lectures greater than subscription videos")
                                            new_dict = category_topics_obj.CategoryLectures[i].dict(
                                            )

                                            video_id = category_topics_obj.CategoryLectures[i].id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            watch_time = await watch_activity(video_id)
                                            new_dict.update(
                                                {"watch_time": watch_time})
                                            access_lectures.append(new_dict)

                                        remaining_counter = len(
                                            category_topics_obj.CategoryLectures) - access_counter
                                        for j in range(remaining_counter):
                                            updated_dict = category_topics_obj.CategoryLectures[access_counter + j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)
                                    else:
                                        for j in range(len(category_topics_obj.CategoryLectures)):
                                            updated_dict = category_topics_obj.CategoryLectures[j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)

                                    sorted_list = sorted(
                                        access_lectures, key=itemgetter('order_display'))
                                    new_lect_dict.update(
                                        {"CategoryLectures": sorted_list})
                                    category_topics_array.append(new_lect_dict)
                                    forward_access_flag = 0

                            elif len(category_topics_obj.CategoryLectures) == subscription_video_counter:
                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    if forward_access_flag:
                                        for eachLecture in category_topics_obj.CategoryLectures:
                                            new_dict = eachLecture.dict()
                                            video_id = eachLecture.id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            watch_time = await watch_activity(video_id)
                                            new_dict.update(
                                                {"watch_time": watch_time})
                                            access_lectures.append(new_dict)

                                    else:
                                        for j in range(len(category_topics_obj.CategoryLectures)):
                                            updated_dict = category_topics_obj.CategoryLectures[j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)

                                    sorted_list = sorted(
                                        access_lectures, key=itemgetter('order_display'))
                                    new_lect_dict.update(
                                        {"CategoryLectures": sorted_list})

                                    category_topics_array.append(new_lect_dict)
                                    forward_access_flag = 0
                                    subscription_video_counter = 0
                                    print("Both are equal")

                            elif (len(category_topics_obj.CategoryLectures) < subscription_video_counter):

                                """ check for is bookmarked"""
                                new_lectures = []
                                if category_topics_obj.CategoryLectures:
                                    if forward_access_flag:
                                        for eachLecture in category_topics_obj.CategoryLectures:
                                            new_dict = eachLecture.dict()
                                            video_id = eachLecture.id
                                            is_bookmarked = await check_isBookmarkedVideo(video_id)
                                            new_dict.update(
                                                {"isBookmarked": is_bookmarked})
                                            is_liked = await check_isLikedVideo(video_id)
                                            new_dict.update(
                                                {"isLiked": is_liked})
                                            watch_time = await watch_activity(video_id)
                                            new_dict.update(
                                                {"watch_time": watch_time})
                                            access_lectures.append(new_dict)
                                            print(
                                                "lectures are less than subscription")
                                    else:
                                        for j in range(len(category_topics_obj.CategoryLectures)):
                                            updated_dict = category_topics_obj.CategoryLectures[j].dict(
                                            )
                                            updated_dict.update(
                                                {'mobile_video_url': None})
                                            updated_dict.update(
                                                {'web_video_url': None})
                                            access_lectures.append(
                                                updated_dict)

                                    # access_lectures.append(new_lectures)

                                    subscription_video_counter -= len(
                                        category_topics_obj.CategoryLectures)
                                    sorted_list = sorted(
                                        access_lectures, key=itemgetter('order_display'))
                                    new_lect_dict.update(
                                        {"CategoryLectures": sorted_list})
                                    category_topics_array.append(new_lect_dict)

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
                                    watch_time = await watch_activity(video_id)
                                    new_dict.update({"watch_time": watch_time})

                                    access_lectures.append(new_dict)

                                # access_lectures.append(new_lectures)

                                sorted_list = sorted(
                                    access_lectures, key=itemgetter('order_display'))
                                new_lect_dict.update(
                                    {"CategoryLectures": sorted_list})

                                category_topics_array.append(new_lect_dict)
                            # category_topics_array.append({"CategoryLectures": access_lectures})

                    return category_topics_array

                async def execute_notes_loop(array, subscription_notes_counter):
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

                async def execute_test_series_loop(array, subscription_series_counter):

                    category_topics_array = []

                    for category_topics_obj in array:
                        access_series = []

                        if total_length_of_test_series > subscription_series_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                                                                     "category"})}

                            if len(category_topics_obj.CategoryTestSeries) > subscription_series_counter:

                                for i in range(subscription_series_counter):
                                    new_dict = category_topics_obj.CategoryTestSeries[i].dict(
                                        exclude={'CategoryTestSeriesQuestions'})
                                    test_series_id = category_topics_obj.CategoryTestSeries[i].id
                                    is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    attempted = await testseries_activity(test_series_id)
                                    new_dict.update({"attempted": attempted})
                                    access_series.append(new_dict)
                                remaining_counter = len(
                                    category_topics_obj.CategoryTestSeries) - subscription_series_counter
                                for j in range(remaining_counter):
                                    updated_dict = category_topics_obj.CategoryTestSeries[
                                        subscription_series_counter + j].dict(exclude={'CategoryTestSeriesQuestions'})
                                    test_series_id = None
                                    # test_series_id = category_topics_obj.CategoryTestSeries[
                                    #     subscription_series_counter + j].id
                                    # is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                    updated_dict.update(
                                        {"id": None})
                                    updated_dict.update(
                                        {"isBookmarked": False})
                                    # attempted = await testseries_activity(test_series_id)
                                    updated_dict.update(
                                        {"attempted": False})
                                    access_series.append(updated_dict)

                                new_lect_dict.update(
                                    {"CategoryTestSeries": access_series})
                                category_topics_array.append(new_lect_dict)
                                # subscription_series_counter = 0

                            if subscription_series_counter and (
                                    len(category_topics_obj.CategoryTestSeries) < subscription_series_counter
                            ):
                                if category_topics_obj.CategoryTestSeries:
                                    for eachTest in category_topics_obj.CategoryTestSeries:
                                        new_dict = eachTest.dict(
                                            exclude={
                                                'CategoryTestSeriesQuestions'}
                                        )
                                        test_series_id = eachTest.id
                                        is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        attempted = await testseries_activity(test_series_id)
                                        new_dict.update(
                                            {"attempted": attempted})

                                        access_series.append(new_dict)
                                    # subscription_series_counter -= len(category_topics_obj.CategoryTestSeries)
                                    new_lect_dict.update(
                                        {"CategoryTestSeries": access_series})

                                    category_topics_array.append(new_lect_dict)

                            if len(category_topics_obj.CategoryTestSeries) == subscription_series_counter:
                                if category_topics_obj.CategoryTestSeries:
                                    for eachTest in category_topics_obj.CategoryTestSeries:
                                        new_dict = eachTest.dict(
                                            exclude={'CategoryTestSeriesQuestions'})
                                        test_series_id = eachTest.id
                                        is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                        new_dict.update(
                                            {"isBookmarked": is_bookmarked})
                                        attempted = await testseries_activity(test_series_id)
                                        new_dict.update(
                                            {"attempted": attempted})
                                        access_series.append(new_dict)
                                        # subscription_series_counter = 0

                                    new_lect_dict.update(
                                        {"CategoryTestSeries": access_series})

                                    category_topics_array.append(new_lect_dict)
                                return category_topics_array

                                # return category_topics_array

                        elif total_length_of_test_series <= subscription_series_counter:
                            new_lect_dict = {"topic": category_topics_obj.topic.dict(exclude={
                                                                                     "category"})}
                            if category_topics_obj.CategoryTestSeries:
                                for eachTest in category_topics_obj.CategoryTestSeries:
                                    new_dict = eachTest.dict(
                                        exclude={'CategoryTestSeriesQuestions'})
                                    test_series_id = eachTest.id
                                    is_bookmarked = await check_isBookmarkedTestSeries(test_series_id)
                                    new_dict.update(
                                        {"isBookmarked": is_bookmarked})
                                    attempted = await testseries_activity(test_series_id)
                                    new_dict.update({"attempted": attempted})
                                    access_series.append(new_dict)
                                new_lect_dict.update(
                                    {"CategoryTestSeries": access_series})

                                category_topics_array.append(new_lect_dict)

                    return category_topics_array

                category_course_ins = await CourseCategories.get(course=course, category=category)
                import pytz
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz)

                if not category_course_ins.is_free:
                    if await activeSubscription.exists(student=student_instance, course=course):

                        active_subscription = await activeSubscription.get(student=student_instance, course=course).values(
                            "subscription__id")

                        subscription_id = active_subscription["subscription__id"]
                        if await StudentChoices.exists(student=student_instance,
                                                       subscription__id=subscription_id, expiry_date__gte=now, payment__payment_status=2):
                            student_choice = await activeSubscription.get(student=student_instance, course=course) \
                                .values("subscription__no_of_videos", "subscription__no_of_notes",
                                        "subscription__no_of_tests", "subscription__live_classes_access")

                            no_of_videos = student_choice["subscription__no_of_videos"]
                            no_of_notes = student_choice["subscription__no_of_notes"]
                            no_of_tests = student_choice["subscription__no_of_tests"]
                            live_classes_access = student_choice["subscription__live_classes_access"]

                            subscription_initial_video_counter = no_of_videos
                            subscription_initial_notes_counter = no_of_notes
                            subscription_initial_test_series_counter = no_of_tests

                            updated_access_lect_array = await execute_lectures_loop(
                                resp, subscription_initial_video_counter)

                            updated_access_notes_array = await execute_notes_loop(
                                resp, subscription_initial_notes_counter)

                            updated_access_test_series_array = await execute_test_series_loop(
                                resp, subscription_initial_test_series_counter)

                            result = {
                                "Lectures": updated_access_lect_array,
                                "Notes": updated_access_notes_array,
                                "TestSeries": updated_access_test_series_array,
                            }

                            return result
                        else:
                            '''Free content free tier'''

                            initial_video_counter = 2
                            initial_notes_counter = 2
                            initial_test_series_counter = 2

                            updated_access_lect_array = await execute_lectures_loop(
                                resp, initial_video_counter)

                            updated_access_notes_array = await execute_notes_loop(
                                resp, initial_notes_counter)

                            updated_access_test_series_array = await execute_test_series_loop(
                                resp, initial_test_series_counter)

                            result = {
                                "Lectures": updated_access_lect_array,
                                "Notes": updated_access_notes_array,
                                "TestSeries": updated_access_test_series_array,
                            }
                            return result

                    else:
                        print("FREE CONTENT EXECUTED")
                        '''Free content free tier'''

                        initial_video_counter = 2
                        initial_notes_counter = 2
                        initial_test_series_counter = 2

                        updated_access_lect_array = await execute_lectures_loop(
                            resp, initial_video_counter)

                        updated_access_notes_array = await execute_notes_loop(
                            resp, initial_notes_counter)

                        updated_access_test_series_array = await execute_test_series_loop(
                            resp, initial_test_series_counter)

                        result = {
                            "Lectures": updated_access_lect_array,
                            "Notes": updated_access_notes_array,
                            "TestSeries": updated_access_test_series_array,
                        }
                        return result

                else:
                    initial_video_counter = total_length_of_lectures
                    initial_notes_counter = total_length_of_notes
                    initial_test_series_counter = total_length_of_test_series

                    updated_access_lect_array = await execute_lectures_loop(
                        resp, initial_video_counter)

                    updated_access_notes_array = await execute_notes_loop(
                        resp, initial_notes_counter)

                    updated_access_test_series_array = await execute_test_series_loop(
                        resp, initial_test_series_counter)

                    result = {
                        "Lectures": updated_access_lect_array,
                        "Notes": updated_access_notes_array,
                        "TestSeries": updated_access_test_series_array,
                    }

                    return result

    except Exception as ex:
        return JSONResponse({'status': False, 'message': str(ex)}, status_code=208)


@router.get('/subscription_plans/course/{course_slug}/{student_id}/',
            response_model=List[CourseSubscriptionPlans_course]
            )
async def subscription_plans(course_slug: str, student_id: str, _=Depends(get_current_user)):
    new_array = []
    c_obj = await Course.get(slug=course_slug)
    category_count = await CourseCategories.filter(course=c_obj, is_free=False).count()
    course_plans = await CourseSubscriptionPlans_Pydantic.from_queryset(
        CourseSubscriptionPlans.filter(is_active=True, course=c_obj).order_by("validity"))
    if await Student.exists(id=student_id):
        student_instance = await Student.get(id=student_id)

        new_validity = 0
        new_price = 0
        existing_validity = 0
        existing_price = 0
        used_months = 0

        for subscription in course_plans:
            subscription_instance = await CourseSubscriptionPlans.get(id=subscription.id)
            # now = datetime.today()
            import pytz
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            if await StudentChoices.exists(student=student_instance,
                                           subscription=subscription_instance,
                                           course=c_obj, expiry_date__gte=now):

                subscribed_obj = await StudentChoices.get(student=student_instance,
                                                          subscription=subscription_instance,
                                                          course=c_obj, expiry_date__gte=now)

                delta = now - subscribed_obj.created_at
                used_months = round(delta.days / 30)

                updated_dict = subscription.dict()
                initial_video_count = updated_dict['no_of_videos']
                initial_notes_count = updated_dict['no_of_notes']
                initial_tests_count = updated_dict['no_of_tests']
                updated_dict.update(
                    {"no_of_videos": initial_video_count * category_count})
                updated_dict.update(
                    {"no_of_notes": initial_notes_count * category_count})
                updated_dict.update(
                    {"no_of_tests": initial_tests_count * category_count})
                updated_dict.update({"is_subscribed": True})
                existing_validity = updated_dict['validity']
                existing_price = updated_dict['plan_price']
                # print(updated_dict)
            else:
                updated_dict = subscription.dict()
                validity = updated_dict['validity']
                plan_price = updated_dict['plan_price']
                if existing_validity and (validity > existing_validity):
                    new_validity = validity - used_months
                    new_price = plan_price - existing_price
                    updated_dict.update(
                        {"validity": new_validity})
                    updated_dict.update(
                        {"plan_price": new_price})
                initial_video_count = updated_dict['no_of_videos']
                initial_notes_count = updated_dict['no_of_notes']
                initial_tests_count = updated_dict['no_of_tests']
                updated_dict.update(
                    {"no_of_videos": initial_video_count * category_count})
                updated_dict.update(
                    {"no_of_notes": initial_notes_count * category_count})
                updated_dict.update(
                    {"no_of_tests": initial_tests_count * category_count})

                updated_dict.update({"is_subscribed": False})
            new_array.append(updated_dict)
        return new_array
    else:
        return JSONResponse({"status": False, "message": "student not found"}, status_code=208)


@router.get('/course/course_overview/{course_slug}/',
            response_model=List[CoursePydantic]
            )
async def course_overview(course_slug: str, _=Depends(get_current_user)):
    course = await Course.get(slug=course_slug)

    overview = await Course_Pydantic.from_queryset(
        Course.filter(slug=course_slug)
    )
    # overview = await CourseCategoryOverview_Pydantic.from_queryset(
    #     CourseCategoryOverview.filter(course=course)
    # )

    # overview = await CourseCategories_Pydantic.from_queryset(
    #     CourseCategories.filter(course=course).limit(1))
    return overview


@router.post('/add_instructor')
async def add_instructor(data: InstructorIn_Pydantic, _=Depends(get_current_user)):
    # if await Instructor.create(**data.dict(exclude_unset=True)):
    if await Instructor.create(name=data.name, slug=slugify(data.name)):
        return {"added successfully"}
    else:
        return {"An error occurred"}


@router.get('/get_instructor/')
async def get_instructor(_=Depends(get_current_user)):
    obj = await Instructor_Pydantic.from_queryset(Instructor.all())
    return obj


@router.get('/add_live_class')
async def add_live_class(title: str, url: str, lecture_duration: str, instructor_id: str,
                         lecture_id: str, streaming_time: datetime, thumbnail: UploadFile = File(...),
                         s3: BaseClient = Depends(s3_auth), _=Depends(get_current_user)):
    instructor = await Instructor.get(id=instructor_id)
    lecture = await CourseCategoryLectures.get(id=lecture_id)
    image_url = await upload_images(s3, folder='live_classes/thumbnails', image=thumbnail, mimetype=None)

    obj = await LiveClasses.create(title=title, url=url, lecture_duration=lecture_duration,
                                   lecture=lecture, instructor=instructor, thumbnail=image_url,
                                   streaming_time=streaming_time)
    if obj:
        return {"details": "added successfully"}
    else:
        return {"An error occurred"}


class InstructorPydantic(BaseModel):
    id: uuid.UUID
    name: str
    image_url: Optional[str] = None


class lecturePydantic(BaseModel):
    description: Optional[str] = None


class LiveClassesPydantic(BaseModel):
    id: uuid.UUID
    title: str
    lecture: lecturePydantic
    instructor: InstructorPydantic
    url: Optional[str] = None
    thumbnail: Optional[str] = None
    streaming_time: Optional[datetime] = None
    lecture_duration: Optional[str] = None

    @validator('streaming_time', pre=True, always=True)
    def set_ts_now(cls, v):
        return v or datetime.now()


class PNCoursePydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class PNLiveClassesPydantic(BaseModel):
    id: uuid.UUID
    title: str
    lecture: lecturePydantic
    instructor: InstructorPydantic
    url: str
    thumbnail: Optional[str] = None
    streaming_time: Optional[datetime] = None
    lecture_duration: Optional[str] = None
    course: PNCoursePydantic

    @validator('streaming_time', pre=True, always=True)
    def set_ts_now(cls, v):
        return v or datetime.now()


@router.get('/get_live_classes/{course_slug}/',
            response_model=List[PNLiveClassesPydantic]
            )
async def get_live_classes(course_slug: str, ):
    obj = await LiveClasses_Pydantic.from_queryset(
        LiveClasses.filter(course__slug=course_slug, is_paid=True).order_by("-created_at"))
    return obj


@router.get('/get_live_classes/v2/{course_slug}/{student_id}/',
            response_model=List[LiveClassesPydantic]
            )
async def get_live_classes(course_slug: str, student_id: str, _=Depends(get_current_user)):
    course = await Course.get(slug=course_slug)
    student = await Student.get(id=student_id)
    subscription = await activeSubscription.exists(course=course, student=student)
    if subscription:
        obj = await LiveClasses_Pydantic.from_queryset(
            LiveClasses.filter(course__slug=course_slug, ))
    else:
        obj = await LiveClasses_Pydantic.from_queryset(
            LiveClasses.filter(course__slug=course_slug, is_paid=False))

    return obj


@router.get('/get_filtered_live_classes/{course_slug}/{student_id}/{d}',
            response_model=List[LiveClassesPydantic]
            )
async def get_live_classes(course_slug: str, student_id: str, d:str, _=Depends(get_current_user)):
    try:
        #parse d as date
        d = datetime.strptime(d, '%Y-%m-%d').date()
        tradeDate = datetime.combine(d, datetime.min.time())

        dt = tz.localize(tradeDate, is_dst=True)
        # tradeDay=dt.astimezone(pytz.utc)
        dt1 = (dt+relativedelta(hours=23, minutes=59, seconds=59))
       
        subscription = await activeSubscription.exists(course__slug=course_slug, student__id=student_id)
        if subscription:
            obj = await LiveClasses_Pydantic.from_queryset(
                LiveClasses.filter(course__slug=course_slug).filter(streaming_time__range=[dt, dt1]))
        else:
            obj = await LiveClasses_Pydantic.from_queryset(
                LiveClasses.filter(course__slug=course_slug, is_paid=False).filter(streaming_time__range=[dt, dt1]))

        return obj
    except Exception as e:
        return JSONResponse({'status': False, 'message': str(e)})


@router.get('/get_all_live_classes/',
            response_model=List[LiveClassesPydantic]
            )
async def get_all_live_classes(_=Depends(get_current_user)):
    obj = await LiveClasses_Pydantic.from_queryset(
        LiveClasses.all())
    return obj


@router.delete('/delete_live_classes/')
async def delete_live_classes(_=Depends(get_current_user)):
    obj = await LiveClasses.all().delete()
    return obj


@router.delete('/delete_subscriptions/')
async def delete_all_subscriptions(_=Depends(get_current_user)):
    await CourseSubscriptionPlans.all().delete()
    return {"all deleted"}


@router.post('/app_static_urls/')
async def add_static_urls(title: str, url: str, _=Depends(get_current_user)):
    if not await addAppStaticUrls.exists(title=title):
        await addAppStaticUrls.create(title=title, url=url)
        return JSONResponse(
            {"status": True, "message": "Submitted"}, status_code=201)


@router.get('/app_static_urls/')
async def static_urls(_=Depends(get_current_user)):
    obj = await addAppStaticUrls_Pydantic.from_queryset(
        addAppStaticUrls.all())
    arr = []
    for stats in obj:
        new_obj = {stats.title: stats.url}
        arr.append(new_obj)
    return arr


@router.post('/offer_banners/')
async def offer_banners(title: str, banner: UploadFile = File(...),
                        s3: BaseClient = Depends(s3_auth), _=Depends(get_current_user)):
    if not await offerBanners.exists(title=title):
        image_url = await upload_images(s3, folder='offer_banners', image=banner, mimetype=None)
        obj = await offerBanners.create(
            title=title,
            url=image_url,
        )
        return JSONResponse(
            {'status': True, 'message': 'banner added'}, status_code=200
        )


@router.get('/offer_banners/')
async def offer_banners():
    obj = await offerBanners_Pydantic.from_queryset(
        offerBanners.all())

    return obj


'''Add coupon'''


@router.post('/add_coupon')
async def add_coupon(name: str, discount: str, coupon_type: int, subscription: str, _=Depends(get_current_user)):
    try:
        if subscription == 'all':
            subscriptions = await CourseSubscriptionPlans.filter(is_active=True).values("id")
            for subscription in subscriptions:
                if not await Coupons.exists(name=name.strip(), subscription__id=subscription["id"]):
                    subscription = await CourseSubscriptionPlans.get(id=subscription["id"])
                    await Coupons.create(
                        name=name.strip(), discount=discount, subscription=subscription, coupon_type=coupon_type)
            return JSONResponse({'status': True, 'message': 'New coupon added'})
        else:
            if not await Coupons.exists(name=name.strip(), subscription__id=subscription.strip()):
                subscription = await CourseSubscriptionPlans.get(id=subscription.strip())
                await Coupons.create(
                    name=name.strip(), discount=discount, subscription=subscription, coupon_type=coupon_type)
                return JSONResponse({'status': True, 'message': 'New coupon added'})
            else:
                return JSONResponse({
                    'status': False, 'message': 'This coupon already exists'}, status_code=208)

    except Exception as ex:
        raise HTTPException(status_code=208, detail=str(ex))


class DashboardPydantic(BaseModel):
    student_id: uuid.UUID


@router.post('/dashboard_count_api/')
async def dashboard_count(data: DashboardPydantic, _=Depends(get_current_user)):
    student_id = data.student_id
    course_count = await activeSubscription.filter(student__id=student_id).count()
    studyMaterial_count = await StudyMaterialOrderInstance.filter(student__id=student_id).count()
    testseries_count = await TestSeriesOrders.filter(student__id=student_id).count()
    resp = {
        "total_orders": course_count + studyMaterial_count + testseries_count,
        "course_orders": course_count,
        "study_material_count": studyMaterial_count,
        "test_series_count": testseries_count
    }

    return resp


@router.get('/get_video_ids/')
async def update_video_id(_=Depends(get_current_user)):
    objs = await CourseCategoryLectures.all()
    # for obj in objs:
    #     app_url = obj.mobile_video_url
    #     video_id = app_url.split('/')[-2]
    #     await CourseCategoryLectures.filter(id=obj.id).update(video_id=video_id)
    # read file
    with open('./videos.json', 'r') as myfile:
        data = myfile.read()

    # parse file
    obj = json.loads(data)
    i = 0
    for item in obj['items']:
        # print(item['length'])

        await CourseCategoryLectures.filter(video_id=item['guid']).update(video_duration=item['length'])
        i = i + 1
    # show values
    # print("usd: " + str(obj['items']))

    return {"updated all"}


@router.post('/check_scholarship_mobile/')
async def checkSchMobile(mobile: str, _=Depends(get_current_user)):
    if await Scholarship2021.exists(mobile=mobile):
        return JSONResponse({"status": False, "message": "Mobile Number is already registered."}, status_code=200)
    else:
        return JSONResponse({"status": True, "message": "Mobile Number not registered."}, status_code=200)


@router.post('/scholarship_form_2021/',)
async def fill_scholarship2021(name: str, email: str, mobile: str,  _=Depends(get_current_user)):
    if await Scholarship2021.exists(email=email):
        return JSONResponse({"status": False, "message": "Email Id is already registered."}, status_code=200)
    elif await Scholarship2021.exists(mobile=mobile):
        return JSONResponse({"status": False, "message": "Mobile Number is already registered."}, status_code=200)
    else:
        await Scholarship2021.create(name=name, email=email, mobile=mobile)
        return JSONResponse({"status": True, "message": "You've successfully registered for Scholarship Test."}, status_code=200)

# ce99f0eb-63eb-4e8f-931f-022ea3d3b6c5


class getCandidates(BaseModel):
    name: str
    email: str
    mobile: str
    roll_no: str


@router.post('/interview/program/2020/')
async def interview_program(s3: BaseClient = Depends(s3_auth), data: getCandidates = Depends(),
                            image: Optional[UploadFile] = File(default=None, media_type='image/*')):
    try:
        if await InterViewProgram.exists(email=data.email):
            return JSONResponse({"status": False, "message": "Email Id is already registered."})
        elif await InterViewProgram.exists(mobile=data.mobile):
            return JSONResponse({"status": False, "message": "Mobile Number is already registered."})
        else:
            folder = 'interview-files/2020'
            image_url = await upload_images(s3, folder=folder, image=image, mimetype=None)

            await InterViewProgram.create(name=data.name, email=data.email,
                                          mobile=data.mobile, roll_no=data.roll_no,
                                          file=image_url)
            return JSONResponse({"status": True, "message": "Registration Successful"})
        # return JSONResponse({"status": False, "message": "An error occured"}, status_code=204)
    except Exception as ex:
        return JSONResponse({"status": False, "message": str(ex)})
