from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise import Tortoise


class ScholarshipTestSeries(Model):
    id = fields.UUIDField(pk=True)
    on_date = fields.DatetimeField(null=True, blank=True)
    end_date = fields.DatetimeField(null=True, blank=True)
    result_announcement_date = fields.DatetimeField(null=True, blank=True)
    title = fields.CharField(80,)
    total_marks = fields.IntField()
    time_duration = fields.IntField()
    no_of_qstns = fields.IntField()
    lang = fields.CharField(5, null=True, blank=True)
    image = fields.TextField(null=True, blank=True)
    description = fields.TextField(null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class ScholarshipTestSeriesQuestions(Model):
    id = fields.UUIDField(pk=True)
    question = fields.TextField()
    opt_1 = fields.TextField()
    opt_2 = fields.TextField()
    opt_3 = fields.TextField()
    opt_4 = fields.TextField()
    answer = fields.CharField(max_length=10)
    solution = fields.TextField(null=True, blank=True)
    test_series = fields.ForeignKeyField(
        "models.ScholarshipTestSeries", related_name="ScholarshipTestSeries", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class StudentScholarshipTestSeriesRecord(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_StudentScholarshipTestSeriesRecord", on_delete='CASCADE',
    )
    correct_ans = fields.IntField()
    wrong_ans = fields.IntField()
    skipped_qns = fields.IntField()
    is_attempted = fields.BooleanField(default=False)
    marks = fields.IntField()
    lang_chosen = fields.CharField(10, null=True, blank=True)
    test_series = fields.ForeignKeyField(
        "models.ScholarshipTestSeries", related_name="ScholarshipTestSeries_student", on_delete='CASCADE',
    )
    time_taken = fields.IntField()
    test_record_summary = fields.TextField()
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


Tortoise.init_models(["scholarship_tests.models", "student.models"], "models")
ScholarshipTestSeries_Pydantic = pydantic_model_creator(ScholarshipTestSeries)
ScholarshipTestSeriesQuestions_Pydantic = pydantic_model_creator(
    ScholarshipTestSeriesQuestions)
StudentScholarshipTestSeriesRecord_Pydantic = pydantic_model_creator(
    StudentScholarshipTestSeriesRecord)
