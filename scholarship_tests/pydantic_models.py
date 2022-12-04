from typing import Optional
from pydantic import BaseModel, Json
import uuid
from typing import List
from pydantic.json import pydantic_encoder
from tortoise.fields.data import JsonLoadsFunc


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
    test_series_id: str
