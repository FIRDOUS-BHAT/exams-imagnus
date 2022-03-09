import uuid
from typing import List, Optional

from pydantic import BaseModel


class CourseCategoryTestSeriesQuestionsOut(BaseModel):
    id: uuid.UUID
    question: str
    opt_1: str
    opt_2: str
    opt_3: str
    opt_4: str
    answer: str
    solution: str

    class Config:
        orm_mode = True


class CourseCategoryTestSeriesOut(BaseModel):
    series_no: Optional[str] = None
    marks: int
    no_of_qstns: int
    title: Optional[str] = None
    time_duration: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    CategoryTestSeriesQuestions: List[CourseCategoryTestSeriesQuestionsOut]

    class Config:
        orm_mode = True


class topicPydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    class Config:
        orm_mode = True


class categoryPydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon_image: str

    # topics: List[topicPydantic]

    class Config:
        orm_mode = True


class CourseOverview(BaseModel):
    id: uuid.UUID
    overview: str
    examination: str
    syllabus: str

    class Config:
        orm_mode = True


class CategoryLecturesPydantic(BaseModel):
    id: uuid.UUID
    title: Optional[str] = None
    slug: Optional[str] = None
    mobile_video_url: Optional[str] = None
    app_thumbnail: Optional[str] = None
    # web_video_url: Optional[str] = None
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
    id: uuid.UUID
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
        orm_mode = True


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
        orm_mode = True


class CoursePydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon_image: Optional[str] = None
    categories: List[CategoriesPydantic]
    course_overview: List[CourseOverview]
    CourseSubscriptionPlans_course: List[CourseSubscriptionPlans_course]

    class Config:
        orm_mode = True


class CourseCategoriesPydantic(BaseModel):
    course: Optional[CoursePydantic]
    category: Optional[CategoriesPydantic]

    class Config:
        orm_mode = True


class EachCategoryPydantic(BaseModel):
    id: uuid.UUID
    # category: categoryPydantic
    categories_topics: List[categories_topicsPydantic]

    class Config:
        orm_mode = True


class LecturesPydantic(BaseModel):
    topic: topicPydantic
    CategoryLectures: List[CategoryLecturesPydantic]

    class Config:
        orm_mode = True


class NotesPydantic(BaseModel):
    topic: topicPydantic
    CategoryNotes: List[CategoryNotesPydantic]

    class Config:
        orm_mode = True


class TestSeriesPydantic(BaseModel):
    topic: topicPydantic
    CategoryTestSeries: List[CategoryTestSeriesPydantic]

    class Config:
        orm_mode = True


class CourseCategoryPydantic(BaseModel):
    Lectures: List[LecturesPydantic]
    Notes: List[NotesPydantic]
    TestSeries: List[TestSeriesPydantic]

    class Config:
        orm_mode = True
