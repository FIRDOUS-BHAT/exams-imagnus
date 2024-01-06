import uuid
from typing import List, Optional

from pydantic import BaseModel,validator


class CourseCategoryTestSeriesQuestionsOut(BaseModel):
    id: uuid.UUID
    question: str
    opt_1: str
    opt_2: str
    opt_3: str
    opt_4: str
    answer: str
    solution: str

    @validator('answer', pre=True)
    def strip_spaces_from_answer(cls, v):
        return v.strip() if isinstance(v, str) else v

    class Config:
        from_attributes = True


class CourseCategoryTestSeriesOut(BaseModel):
    series_no: Optional[str] = None
    marks: int
    no_of_qstns: int
    title: Optional[str] = None
    time_duration: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    CategoryTestSeriesQuestions: List[CourseCategoryTestSeriesQuestionsOut]

    @validator('time_duration', pre=True)
    def convert_duration_to_str(cls, v):
        if isinstance(v, int):
            return str(v)
        return v

    class Config:
        from_attributes = True


class topicPydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    class Config:
        from_attributes = True


class categoryPydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon_image: str

    # topics: List[topicPydantic]

    class Config:
        from_attributes = True


class CourseOverview(BaseModel):
    id: uuid.UUID
    overview: str
    examination: str
    syllabus: str

    class Config:
        from_attributes = True


class CategoryLecturesPydantic(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    slug: Optional[str] = None
    mobile_video_url: Optional[str] = None
    app_thumbnail: Optional[str] = None
    web_video_url: Optional[str] = None
    video_id: Optional[str] = None
    video_duration: Optional[float] = None
    discription: Optional[str] = None
    isBookmarked: Optional[bool] = False
    isLiked: Optional[bool] = False
    watch_time: Optional[str] = None


class CategoryNotesPydantic(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    slug: Optional[str] = None
    notes_url: Optional[str] = None
    thumbnail: Optional[str] = None
    isBookmarked: Optional[bool] = False
    last_seen: Optional[str] = None


class CategoryTestSeriesPydantic(BaseModel):
    id: Optional[uuid.UUID] = None
    series_no: Optional[str] = None
    time_duration: Optional[int] = None
    marks: Optional[int] = None
    no_of_qstns: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    isBookmarked: Optional[bool] = False
    attempted: Optional[bool] = False


class categories_topicsPydantic(BaseModel):
    topic: topicPydantic
    CategoryLectures: List[CategoryLecturesPydantic]
    CategoryNotes: List[CategoryNotesPydantic]
    CategoryTestSeries: List[CategoryTestSeriesPydantic]


class CategoriesPydantic(BaseModel):
    id: uuid.UUID
    category: categoryPydantic

    categories_topics: List[categories_topicsPydantic]

    class Config:
        from_attributes = True


class CourseCategoriesCount(BaseModel):
    id: uuid.UUID
    category: categoryPydantic
    lectures: int
    notes: int
    test_series: int


class subscriptionPlansPydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    sub_title: str
    icon_image: str


class CourseSubscriptionPlans_course(BaseModel):
    id: uuid.UUID
    SubscriptionPlan: subscriptionPlansPydantic
    validity: int
    plan_price: int
    no_of_videos: int
    no_of_notes: int
    no_of_tests: int
    live_classes_access: bool
    plan_features: Optional[str] = None
    is_subscribed: Optional[bool] = False

    class Config:
        from_attributes = True


class CoursePydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon_image: Optional[str] = None
    categories: List[CategoriesPydantic]
    course_overview: List[CourseOverview]
    CourseSubscriptionPlans_course: List[CourseSubscriptionPlans_course]

    class Config:
        from_attributes = True


class CourseCategoriesPydantic(BaseModel):
    course: Optional[CoursePydantic]
    category: Optional[CategoriesPydantic]

    class Config:
        from_attributes = True


class EachCategoryPydantic(BaseModel):
    id: uuid.UUID
    # category: categoryPydantic
    categories_topics: List[categories_topicsPydantic]

    class Config:
        from_attributes = True


class LecturesPydantic(BaseModel):
    topic: topicPydantic
    CategoryLectures: List[CategoryLecturesPydantic]

    class Config:
        from_attributes = True


class NotesPydantic(BaseModel):
    topic: topicPydantic
    CategoryNotes: List[CategoryNotesPydantic]

    class Config:
        from_attributes = True


class TestSeriesPydantic(BaseModel):
    topic: topicPydantic
    CategoryTestSeries: List[CategoryTestSeriesPydantic]

    class Config:
        from_attributes = True


class CourseCategoryPydantic(BaseModel):
    Lectures: List[LecturesPydantic]
    Notes: List[NotesPydantic]
    TestSeries: List[TestSeriesPydantic]

    class Config:
        from_attributes = True
