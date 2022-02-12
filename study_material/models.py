from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise import Tortoise
from enum import IntEnum


class PackageMode(IntEnum):
    single = 1
    bundle = 2


class StudyMaterialName(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    slug = fields.CharField(max_length=250, unique=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "StudyMaterialName"

    def __str__(self):
        return self.name


class StudyMaterialCourse(Model):
    id = fields.UUIDField(pk=True)
    course = fields.ForeignKeyField(
        "models.Course", related_name="study_material_course", on_delete='CASCADE',
    )
    mobile_image = fields.TextField(null=True, blank=True)
    web_icon = fields.TextField(null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    bundle_price = fields.IntField(default=0)
    bundle_dsc_price = fields.IntField(default=0)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    material = fields.ForeignKeyField(
        "models.StudyMaterialName", related_name="StudyMaterialName", on_delete='CASCADE',
    )


class StudyMaterialCategories(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    slug = fields.CharField(max_length=250, unique=True)
    topic_name = fields.CharField(max_length=100, unique=True)
    topic_slug = fields.CharField(max_length=250, unique=True)
    price = fields.IntField(default=0)
    discount_price = fields.IntField(default=0)
    mobile_image = fields.TextField(null=True, blank=True)
    web_icon = fields.TextField(null=True, blank=True)
    material_url_key = fields.CharField(1000, null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    course = fields.ForeignKeyField(
        "models.StudyMaterialCourse", related_name="StudyMaterialCourse", on_delete='CASCADE',
    )


class StudyMaterialCartInstance(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="student_StudyMaterialCartInstance", on_delete='CASCADE',
    )
    item_id = fields.ForeignKeyField(
        "models.StudyMaterialCategories", related_name="item_id_StudyMaterialCartInstance", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class PayStatus(IntEnum):
    pending = 1
    confirmed = 2


class StudyMaterialOrderInstance(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="student_StudyMaterialOrderInstance", on_delete='CASCADE',
    )
    # course = fields.ForeignKeyField(
    #     "models.StudyMaterialCourse", related_name="StudyMaterialTSCourse", on_delete='CASCADE',
    # )
    package_mode = fields.IntEnumField(PackageMode, default=PackageMode.single)
    razorpay_payment_id = fields.CharField(250, null=True, blank=True)
    razorpay_order_id = fields.CharField(250, null=True, blank=True)
    bill_amount = fields.IntField(null=True, blank=True)
    payment_status = fields.IntEnumField(
        PayStatus, default=PayStatus.pending)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class StudyMaterialOrderItems(Model):
    id = fields.UUIDField(pk=True)
    order = fields.ForeignKeyField(
        "models.StudyMaterialOrderInstance", related_name="order_StudyMaterialOrderInstance", on_delete='CASCADE',
    )
    item_id = fields.ForeignKeyField(
        "models.StudyMaterialCategories", related_name="item_id_StudyMaterialOrder", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(add_auto_now=True)


class MaterialDownloadRecord(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="StudentMaterialDownloadRecord", on_delete='CASCADE',
    )
    material = fields.ForeignKeyField(
        "models.StudyMaterialCategories", related_name="MaterialMaterialDownloadRecord", on_delete='CASCADE',
    )
    download_count = fields.IntField(default=0)
    download_limit = fields.IntField(default=2)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class StudyMaterialTestSeries(Model):
    id = fields.UUIDField(pk=True)
    cat_name = fields.CharField(max_length=100, unique=True)
    cat_slug = fields.CharField(max_length=250, unique=True)
    topic_name = fields.CharField(max_length=100, unique=True)
    topic_slug = fields.CharField(max_length=250, unique=True)
    time_duration = fields.IntField()
    marks = fields.IntField()
    no_of_qstns = fields.IntField()
    thumbnail = fields.TextField(null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    course = fields.ForeignKeyField(
        "models.StudyMaterialCourse", related_name="StudyMaterialTSCourse", on_delete='CASCADE',
    )


class StudyMaterialTestSeriesQuestions(Model):
    id = fields.UUIDField(pk=True)
    question = fields.TextField()
    opt_1 = fields.TextField()
    opt_2 = fields.TextField()
    opt_3 = fields.TextField()
    opt_4 = fields.TextField()
    answer = fields.CharField(max_length=10)
    solution = fields.TextField()
    test_series = fields.ForeignKeyField(
        "models.StudyMaterialTestSeries", related_name="StudyMaterialTSQuestions", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class TestSeriesOrders(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="student_TestSeriesOrders", on_delete='CASCADE',
    )
    test_series = fields.ForeignKeyField(
        "models.StudyMaterialCourse", related_name="ts_TestSeriesOrders", on_delete='CASCADE',
    )
    razorpay_payment_id = fields.CharField(250, null=True, blank=True)
    razorpay_order_id = fields.CharField(250, null=True, blank=True)
    bill_amount = fields.IntField(null=True, blank=True)
    payment_status = fields.IntEnumField(
        PayStatus, default=PayStatus.pending)
    source = fields.CharField(3, default='app')
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(add_auto_now=True)


Tortoise.init_models(["study_material.models",
                     "admin_dashboard.models", "student.models", ], "models")
StudyMaterialName_Pydantic = pydantic_model_creator(StudyMaterialName)
StudyMaterialCourse_Pydantic = pydantic_model_creator(StudyMaterialCourse)
StudyMaterialCategories_Pydantic = pydantic_model_creator(
    StudyMaterialCategories)
StudyMaterialOrderInstance_Pydantic = pydantic_model_creator(
    StudyMaterialOrderInstance)
StudyMaterialOrderItems_Pydantic = pydantic_model_creator(
    StudyMaterialOrderItems)
StudyMaterialTestSeries_Pydantic = pydantic_model_creator(
    StudyMaterialTestSeries)


TestSeriesOrders_Pydantic = pydantic_model_creator(TestSeriesOrders)
