from datetime import datetime
from enum import IntEnum

from tortoise import Tortoise
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Mode(IntEnum):
    online = 1
    offline = 2
    sales_team = 3


class PayStatus(IntEnum):
    pending = 1
    confirmed = 2


class PaymentRecords(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="registered_student", on_delete='CASCADE',
    )
    subscription = fields.ForeignKeyField(
        "models.CourseSubscriptionPlans", related_name="student_subscription", on_delete='CASCADE',
    )
    payment_mode = fields.IntEnumField(Mode, default=Mode.online)
    payment_status = fields.IntEnumField(PayStatus, default=PayStatus.pending)
    payment_id = fields.CharField(max_length=150, null=True, blank=True)
    order_id = fields.CharField(150, null=True, blank=True)
    gateway_name = fields.CharField(max_length=100, null=True, blank=True)
    coupon = fields.CharField(max_length=100, null=True, blank=True)
    coupon_discount = fields.FloatField(null=True, blank=True)
    # is_partial_payment = fields.BooleanField(default=False)
    notes = fields.TextField(null=True, blank=True)
    source = fields.CharField(3, default='app')
    bill_amount = fields.IntField(null=True, blank=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(default=datetime.utcnow)



class paymentSession(Model):
    txn_id = fields.CharField(max_length=500)
    student = fields.CharField(max_length=500)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class OrderTypeModes(IntEnum):
    course = 1
    material = 2
    testseries = 3


class MobileCart(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="mobile_cart", on_delete='CASCADE',
    )
    order_id = fields.CharField(100, unique=True)
    order_type = fields.IntEnumField(
        OrderTypeModes, default=OrderTypeModes.material)
    subscription_ids = fields.TextField()
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


Tortoise.init_models(["checkout.models", "student.models",
                     "admin_dashboard.models"], "models")
PaymentRecords_Pydantic = pydantic_model_creator(PaymentRecords)
PaymentRecordsIn_Pydantic = pydantic_model_creator(
    PaymentRecords, name="PaymentRecordsIn", exclude_readonly=True)
