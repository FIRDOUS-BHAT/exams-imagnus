from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise import Tortoise


class StudentEnquriry(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(70)
    email = fields.CharField(100, unique=True)
    mobile = fields.CharField(10, unique=True)
    course = fields.CharField(80)
    message = fields.TextField()
    city = fields.CharField(100, null=True, blank=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


Tortoise.init_models(["send_mails.models", ], "models")
StudentEnquriry_Pydantic = pydantic_model_creator(StudentEnquriry)
StudentEnquriryIn_Pydantic = pydantic_model_creator(
    StudentEnquriry, name="StudentEnquriry", exclude_readonly=True)
