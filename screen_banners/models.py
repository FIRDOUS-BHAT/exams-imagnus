from tortoise import Tortoise
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class ScreenBanners(Model):
    """
    This references a Tournament
    """
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    image_url = fields.TextField()
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "screen_banners"

    def __str__(self):
        return self.name


Tortoise.init_models(["screen_banners.models", ], "models")
ScreenBanners_Pydantic = pydantic_model_creator(ScreenBanners)
