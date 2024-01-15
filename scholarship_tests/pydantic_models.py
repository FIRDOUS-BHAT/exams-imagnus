from typing import Optional
from pydantic import BaseModel, validator
import uuid
from typing import List
from pydantic.json import pydantic_encoder
from tortoise.fields.data import JsonLoadsFunc
from datetime import datetime 

class studentIdPydanctic(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    lang: Optional[str] = None


class testRecordIn_Pydantic(BaseModel):
    student_id: str
    test_series_id: str
    correct_ans: int
    wrong_ans: int
    skipped_qns: int
    time_taken: int
    test_record_summary: str


class rankPydantic(BaseModel):
    student_id: str


class rankTopTenPydantic(BaseModel):
    id: str
    marks: int
    time_taken: int
    student_id: uuid.UUID
    test_series_id: uuid.UUID
    student_name: str


class scholarshipTestSeriesPydantic(BaseModel):
    id: uuid.UUID
    test_series_id: uuid.UUID
    opt_1: str
    opt_2: str
    opt_3: str
    opt_4: str
    solution: str
    question: str
    answer: str
   

    @validator('answer')
    def trim_whitespace(cls, v):
        print("called")
        return v.strip()




class rankTestSeriesPydantic(BaseModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID
    result_announcement_date: datetime
    lang: str
    on_date: datetime
    end_date: datetime
    image: str
    description: str
    total_marks: int
    no_of_qstns: int
    is_active: bool
    time_duration: int
    ScholarshipTestSeries: List[scholarshipTestSeriesPydantic]

    class Config:
        from_attributes = True



class rankResponseMessagePydantic(BaseModel):
    rank: str
    top_ten: List[rankTopTenPydantic]
    test_series_obj: rankTestSeriesPydantic

    class Config:
        from_attributes = True
   

class rankResponsePydantic(BaseModel):
    status: bool
    message: rankResponseMessagePydantic

    class Config:
        from_attributes = True