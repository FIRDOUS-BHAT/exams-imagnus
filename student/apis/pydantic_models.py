import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, validator


# class studentChoice_subscriptionPydantic(BaseModel):


class SubscriptionPlanPydantic(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class subscriptionPydantic(BaseModel):
    id: uuid.UUID
    SubscriptionPlan: SubscriptionPlanPydantic
    validity: int
    plan_price: int
    created_at: str

    class Config:
        from_attributes = True


class categoryPydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon_image: Optional[str]

    class Config:
        from_attributes = True


class CoursePydantic(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    telegram_link: Optional[str] = None


class categoryobjPydantic(BaseModel):
    id: uuid.UUID
    category: categoryPydantic

    class Config:
        from_attributes = True


class PNcategoryobjPydantic(BaseModel):
    id: uuid.UUID
    category: categoryPydantic
    course: CoursePydantic

    class Config:
        from_attributes = True


class categorytopicPydantic(BaseModel):
    id: uuid.UUID
    category: categoryobjPydantic

    class Config:
        from_attributes = True



class PNcategorytopicPydantic(BaseModel):
    id: uuid.UUID
    category: PNcategoryobjPydantic

    class Config:
        from_attributes = True


class StudentSubscriptionPydantic(BaseModel):
    subscription: subscriptionPydantic
    expiry_date: str
    course: CoursePydantic
    time_left: str

    class Config:
        from_attributes = True


class studentPydantic(BaseModel):
    id: uuid.UUID
    fullname: str
    mobile: str
    email: str
    dp: Optional[str] = None
    created_at: str
    subscriptions: List[StudentSubscriptionPydantic]

    class Config:
        from_attributes = True


class loginResponsePydantic(BaseModel):
    status: bool
    message: studentPydantic

    class Config:
        from_attributes = True


class StudentChoices_Pydantic:
    pass


# class PaymentRecords(BaseModel):
class CategoryLecturesPydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    mobile_video_url: str
    app_thumbnail: str


class StudentVideoActivityPydanticIn(BaseModel):
    student_id: uuid.UUID
    video_id: uuid.UUID
    watch_time: str
    video_duration: Optional[int] = 0


class StudentNotesActivityPydanticIn(BaseModel):
    student_id: uuid.UUID
    note_id: uuid.UUID


class StudentTestSeriesActivityIn(BaseModel):
    student_id: uuid.UUID
    test_series_id: str


class coursePydantic(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    slug: Optional[str] = None

    class Config:
        from_attributes = True


class eachNewtestSeriesPydantic(BaseModel):
    id: uuid.UUID
    series_no: Optional[int] = 0
    time_duration: int
    marks: int
    no_of_qstns: int
    title: str
    description: Optional[str] = None
    thumbnail: str
    category_topic: categorytopicPydantic


class newtestSeriesPydantic(BaseModel):
    id: uuid.UUID
    series_no: Optional[int] = 0
    time_duration: Optional[int] = 0
    marks: int
    no_of_qstns: int
    title: str
    description: Optional[str] = None
    thumbnail: str
    is_active: bool
    updated_at: datetime = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class eachNotePydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    notes_url: str
    thumbnail: str
    category_topic: categorytopicPydantic


class notePydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    notes_url: str
    thumbnail: str
    updated_at: Optional[datetime] = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class videoPydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    mobile_video_url: str
    web_video_url: Optional[str] = None
    app_thumbnail: Optional[str] = None
    library_id: Optional[str] = None
    video_id: Optional[str] = None
    video_duration: Optional[str] = None
    discription: Optional[str] = None
    updated_at: datetime = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class studentTestSeriesActivityPydantic(BaseModel):
    id: uuid.UUID
    category: categoryPydantic
    test_series_id: Optional[newtestSeriesPydantic] = None
    updated_at: Optional[datetime] = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class studentNotesActivityPydantic(BaseModel):
    id: uuid.UUID
    category: categoryPydantic
    note_id: notePydantic
    last_seen: Optional[str] = None
    updated_at: datetime = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class studentVideoActivityPydantic(BaseModel):
    id: uuid.UUID
    category: Optional[categoryPydantic]
    video_id: Optional[videoPydantic]
    watch_time: Optional[int]
    updated_at: Optional[datetime] = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class ActivityPydantic(BaseModel):
    id: uuid.UUID
    course: coursePydantic
    studentVideoActivity: Optional[List[studentVideoActivityPydantic]] = None
    studentNotesActivity: Optional[List[studentNotesActivityPydantic]] = None
    studentTestSeriesActivity: Optional[List[studentTestSeriesActivityPydantic]] = None

    class Config:
        from_attributes = True


class test_seriesPydantic(BaseModel):
    id: uuid.UUID
    series_no: int
    time_duration: str
    marks: str
    no_of_qstns: str
    title: str
    description: Optional[str] = None
    thumbnail: str
    is_active: bool
    updated_at: datetime = None
    created_at: datetime = None

    @validator('updated_at', pre=True, always=True)
    def set_updated_at(cls, v):
        return v or datetime.now()

    @validator('created_at', pre=True, always=True)
    def set_created_at(cls, v):
        return v or datetime.now()

    class Config:
        from_attributes = True


class testSeriesPydantic(BaseModel):
    test_series: test_seriesPydantic
    category: categoryPydantic

    class Config:
        from_attributes = True


class notesPydantic(BaseModel):
    notes: notePydantic
    category: categoryPydantic

    class Config:
        from_attributes = True


class videosPydantic(BaseModel):
    video: videoPydantic
    category: categoryPydantic

    class Config:
        from_attributes = True


class GetBookmarksPydantic(BaseModel):
    videos: Optional[List[videosPydantic]] = None
    notes: Optional[List[notesPydantic]] = None
    test_series: Optional[List[testSeriesPydantic]] = None

    class Config:
        from_attributes = True


class RecommendedLecturesPydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    mobile_video_url: Optional[str] = None
    app_thumbnail: str
    web_video_url: Optional[str] = None
    app_thumbnail: Optional[str] = None
    library_id: Optional[str] = None
    video_id: Optional[str] = None
    video_duration: Optional[str] = None
    discription: Optional[str] = None
    updated_at: datetime = None
    created_at: datetime = None
    category_topic: categorytopicPydantic

    @validator('video_duration', pre=True)
    def convert_duration_to_str(cls, v):
        if isinstance(v, float):
            return str(v)
        return v

    class Config:
        from_attributes = True


class PNeachNewtestSeriesPydantic(BaseModel):
    id: uuid.UUID
    series_no: Optional[int] = 0
    time_duration: int
    marks: int
    no_of_qstns: int
    title: str
    description: Optional[str] = None
    thumbnail: str
    category_topic: PNcategorytopicPydantic

    class Config:
        from_attributes = True


class PNeachNotePydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    notes_url: str
    thumbnail: str
    category_topic: PNcategorytopicPydantic

    class Config:
        from_attributes = True


class PushNotificationsLecturesPydantic(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    mobile_video_url: str
    app_thumbnail: str
    web_video_url: Optional[str] = None
    app_thumbnail: Optional[str] = None
    library_id: Optional[str] = None
    video_id: Optional[str] = None
    video_duration: Optional[str] = None
    discription: Optional[str] = None
    updated_at: datetime = None
    created_at: datetime = None
    category_topic: PNcategorytopicPydantic

    class Config:
        from_attributes = True


class queryPydantic(BaseModel):
    id: uuid.UUID
    enquiry: str
    category: categoryPydantic
    image: Optional[str] = None
    reply: Optional[str] = None
    is_replied: bool
    created_at: datetime = None

    @validator('created_at', pre=True, always=True)
    def set_ts_now(cls, v):
        return v or datetime.now()
