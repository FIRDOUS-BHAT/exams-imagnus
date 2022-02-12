import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from student.apis.pydantic_models import CoursePydantic


class StudyMaterialCourses(BaseModel):
    id: uuid.UUID
    course: CoursePydantic
    web_icon: str


class StudyMaterialNotes(BaseModel):
    id: uuid.UUID
    name: str
    topic_name: str
    price: int
    discount_price: int
    web_icon: str
    is_purchased: bool


class TestSeriesCourse(BaseModel):
    bundle_price: int
    bundle_dsc_price: str


class StudyMaterialTestSeriesPydantic(BaseModel):
    id: uuid.UUID
    cat_name: str
    topic_name: str
    time_duration: int
    marks: int
    no_of_qstns: int
    thumbnail: str


class StudyMaterialTesSeriesBundlePydantic(BaseModel):
    id: uuid.UUID
    web_icon: str
    bundle_price: str
    bundle_dsc_price: str
    is_purchased: bool


class StudyMaterialContent(BaseModel):
    label: str
    count: Optional[int] = None


class StudyMaterialContentV1(BaseModel):
    label_id: uuid.UUID
    label: str
    count: Optional[int] = None


class StudyMaterialScreen(BaseModel):
    content: List[StudyMaterialContent]
    recommendedNotes: List[StudyMaterialNotes]

    class Config:
        orm_mode = True


class recommendedTestSeriesPydantic(BaseModel):
    id: uuid.UUID
    cat_name: str
    cat_slug: str
    topic_name: str
    topic_slug: str
    no_of_qstns: int
    marks: int
    time_duration: int
    thumbnail: str
    is_purchased: bool


class StudyMaterialScreenV1(BaseModel):
    content: List[StudyMaterialContentV1]
    recommendedNotes: List[StudyMaterialNotes]
    recommendedTestSeries: List[recommendedTestSeriesPydantic]

    class Config:
        orm_mode = True


class orderItems(BaseModel):
    id: uuid.UUID
    name: str
    topic_name: str
    price: int
    discount_price: int
    web_icon: str


class ordersPydantic(BaseModel):
    item_id: orderItems


class studentCoursePydantic(BaseModel):
    course: CoursePydantic


class StudentPydantic(BaseModel):
    student: List[studentCoursePydantic]


class orderHistoryPydactic(BaseModel):
    id: uuid.UUID
    bill_amount: int
    created_at: datetime
    student: StudentPydantic
    order_StudyMaterialOrderInstance: List[ordersPydantic]

    class Config:
        orm_mode = True


class TestSeriesBundleInputParams(BaseModel):
    course_id: str
    label_id: str
    student_id: str


class TestSeriesInputParams(BaseModel):
    bundle_id: str
    student_id: str


class TestSeriesQuestions(BaseModel):
    id: uuid.UUID
    question: str
    opt_1: str
    opt_2: str
    opt_3: str
    opt_4: str
    answer: str


class OrderParams(BaseModel):
    student_id: uuid.UUID
    item_id: Optional[List[uuid.UUID]] = None
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: Optional[str] = None
    bill_amount: int
    package_mode: int


class TestSeriesOrder(BaseModel):
    student_id: uuid.UUID
    item_id: uuid.UUID
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: Optional[str] = None
    bill_amount: int
    package_mode: int


class StudyMaterialTSCoursePydantic(BaseModel):
    id: uuid.UUID
    cat_name: str
    cat_slug: str
    topic_name: str
    topic_slug: str
    time_duration: int
    marks: int
    no_of_qstns: str
    thumbnail: str


class test_seriesPydantic(BaseModel):
    course: CoursePydantic
    StudyMaterialTSCourse: List[StudyMaterialTSCoursePydantic]


class TestSeriesOrderHistory(BaseModel):
    id: uuid.UUID
    razorpay_payment_id: str
    bill_amount: int
    created_at: datetime = None
    test_series: test_seriesPydantic
