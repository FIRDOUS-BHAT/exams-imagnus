from pydantic import BaseModel, Field
from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise import Tortoise


class StudentChoices(Model):
    """
    This references a student subscribed plans
    """

    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="student", on_delete='CASCADE',
    )

    course = fields.ForeignKeyField(
        "models.Course", related_name="student_course", on_delete='CASCADE',
    )
    subscription = fields.ForeignKeyField(
        "models.CourseSubscriptionPlans", related_name="studentChoice_subscription", on_delete='CASCADE',
    )
    payment = fields.ForeignKeyField(
        "models.PaymentRecords", related_name="student_PaymentRecords", on_delete='CASCADE',
    )
    subscription_duration = fields.IntField()
    expiry_date = fields.DatetimeField(null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class activeSubscription(Model):
    id = fields.UUIDField(pk=True)
    subscription = fields.ForeignKeyField(
        "models.CourseSubscriptionPlans", related_name="active_subscription", on_delete='CASCADE',
    )
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_active_subscription", on_delete='CASCADE',
    )
    course = fields.ForeignKeyField(
        "models.Course", related_name="students_active_course", on_delete='CASCADE',
    )
    payment = fields.ForeignKeyField(
        "models.PaymentRecords", related_name="activePayment_PaymentRecords", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class studentActivity(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_studentActivity", on_delete='CASCADE',
    )
    course = fields.ForeignKeyField(
        "models.Course", related_name="course_studentActivity", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class studentVideoActivity(Model):
    id = fields.UUIDField(pk=True)
    student_activity = fields.ForeignKeyField(
        "models.studentActivity", related_name="studentVideoActivity", on_delete='CASCADE',
    )
    category = fields.ForeignKeyField(
        "models.Category", related_name="category_studentVideoActivity", on_delete='CASCADE',
    )
    video_id = fields.ForeignKeyField(
        "models.CourseCategoryLectures", related_name="video_studentVideoActivity", on_delete='CASCADE',
    )
    video_duration = fields.IntField(default=0)
    watch_time = fields.CharField(max_length=10, blank=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class studentNotesActivity(Model):
    id = fields.UUIDField(pk=True)
    student_activity = fields.ForeignKeyField(
        "models.studentActivity", related_name="studentNotesActivity", on_delete='CASCADE',
    )
    category = fields.ForeignKeyField(
        "models.Category", related_name="category_studentNotesActivity", on_delete='CASCADE',
    )
    note_id = fields.ForeignKeyField(
        "models.CourseCategoryNotes", related_name="notes_studentNotesActivity", on_delete='CASCADE',
    )
    last_seen = fields.CharField(max_length=200, blank=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class studentTestSeriesActivity(Model):
    id = fields.UUIDField(pk=True)
    student_activity = fields.ForeignKeyField(
        "models.studentActivity", related_name="studentTestSeriesActivity", on_delete='CASCADE',
    )
    category = fields.ForeignKeyField(
        "models.Category", related_name="category_studentTestSeriesActivity", on_delete='CASCADE',
    )
    test_series_id = fields.ForeignKeyField(
        "models.CourseCategoryTestSeries", related_name="test_series_studentTestSeriesActivity", on_delete='CASCADE',
    )
    attempted = fields.BooleanField(default=False)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class BookMarkedVideos(Model):
    id = fields.UUIDField(pk=True, index=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_bookmarked", on_delete='CASCADE', index=True
    )
    video = fields.ForeignKeyField(
        "models.CourseCategoryLectures", related_name="students_bookmarked_video", on_delete='CASCADE', index=True
    )
    isBookmarked = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class BookMarkedNotes(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_notes_bookmarked", on_delete='CASCADE', index=True
    )
    notes = fields.ForeignKeyField(
        "models.CourseCategoryNotes", related_name="students_bookmarked_notes", on_delete='CASCADE', index=True
    )
    category = fields.ForeignKeyField(
        "models.Category", related_name="category_BookMarkedNotes", on_delete='CASCADE', index=True
    )
    isBookmarked = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class BookMarkedTestseries(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="students_testseries_bookmarked", on_delete='CASCADE', index=True
    )
    test_series = fields.ForeignKeyField(
        "models.CourseCategoryTestSeries", related_name="students_bookmarked_testseries", on_delete='CASCADE', index=True
    )
    category = fields.ForeignKeyField(
        "models.Category", related_name="category_BookMarkedTestseries", on_delete='CASCADE', index=True
    )
    isBookmarked = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Ask(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="ask_student", on_delete='CASCADE', index=True
    )
    category = fields.ForeignKeyField(
        "models.Category", related_name="category_ask", on_delete='CASCADE',  index=True
    )
    enquiry = fields.TextField()
    image = fields.TextField(blank=True, null=True)
    reply = fields.TextField(blank=True, null=True)
    is_replied = fields.BooleanField(default=False)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


Tortoise.init_models(["student.models", "admin_dashboard.models", "student_choices.models", "checkout.models"],
                     "models")
StudentChoice_Pydantic = pydantic_model_creator(StudentChoices)
StudentChoiceIn_Pydantic = pydantic_model_creator(
    StudentChoices, name="StudentChoiceIn", exclude_readonly=True)

studentActivity_Pydantic = pydantic_model_creator(studentActivity)
studentActivityIn_Pydantic = pydantic_model_creator(studentActivity, name="studentActivityIn",
                                                    exclude_readonly=True)
studentNotesActivity_Pydantic = pydantic_model_creator(studentNotesActivity)
studentNotesActivityIn_Pydantic = pydantic_model_creator(studentNotesActivity, name="studentNotesActivityIn",
                                                         exclude_readonly=True)
studentTestSeriesActivity_Pydantic = pydantic_model_creator(
    studentTestSeriesActivity)
studentTestSeriesActivityIn_Pydantic = pydantic_model_creator(studentTestSeriesActivity,
                                                              name="studentTestSeriesActivityIn", exclude_readonly=True)

activeSubscription_Pydantic = pydantic_model_creator(activeSubscription)
ask_Pydantic = pydantic_model_creator(Ask)

BookMarkedVideos_Pydantic = pydantic_model_creator(BookMarkedVideos)

BookMarkedNotes_Pydantic = pydantic_model_creator(BookMarkedNotes)

BookMarkedTestseries_Pydantic = pydantic_model_creator(BookMarkedTestseries)
