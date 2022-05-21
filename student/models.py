from pydantic import BaseModel, Field
from tortoise import Tortoise
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Token(BaseModel):
    access_token: str
    token_type: str
    # expired_in: str


class UserIn(BaseModel):
    mobile: str = Field(..., )
    password: str = Field(..., )


class UserList(BaseModel):
    id: str
    fullname: str
    mobile: str
    email: str
    status: str
    created_at: str


class UserMobileCheck(BaseModel):
    mobile: str = Field(..., )


class Student(Model):
    id = fields.UUIDField(pk=True)
    fullname = fields.CharField(max_length=100)
    mobile = fields.CharField(max_length=10, unique=True)
    email = fields.CharField(max_length=80, unique=True)
    dp = fields.TextField(null=True, blank=True)
    fcm_token = fields.TextField(null=True, blank=True)
    password = fields.CharField(max_length=250)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class StudentTestSeriesRecord(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_StudentTestSeriesRecord", on_delete='CASCADE',
    )
    test_series = fields.ForeignKeyField(
        "models.CourseCategoryTestSeries", related_name="students_CategoryTestSeriesQuestions", on_delete='CASCADE',
    )
    correct_ans = fields.IntField()
    wrong_ans = fields.IntField()
    skipped_qns = fields.IntField()
    marks = fields.IntField()
    test_record_summary = fields.TextField(null=True,blank=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class UsedCoupons(Model):
    id = fields.UUIDField(pk=True)
    coupon = fields.ForeignKeyField(
        "models.Coupons", related_name="coupon_used", on_delete='CASCADE',
    )
    student = fields.ForeignKeyField(
        "models.Student", related_name="coupon_used", on_delete='CASCADE',
    )

    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


Tortoise.init_models(["student.models", "admin_dashboard.models", ], "models")
Student_Pydantic = pydantic_model_creator(Student)
StudentIn_Pydantic = pydantic_model_creator(
    Student, name="StudentIn", exclude_readonly=True)


class UserPWD(UserList):
    password: str
