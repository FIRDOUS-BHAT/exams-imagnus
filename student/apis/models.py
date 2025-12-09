
from tortoise.models import Model
from tortoise import fields


class CourseCategoryLectures(Model):
    id = fields.UUIDField(pk=True, index=True)
    title = fields.CharField(max_length=250, )
    slug = fields.CharField(max_length=550, )
    mobile_video_url = fields.TextField(null=True, blank=True)
    web_video_url = fields.TextField(null=True, blank=True)
    app_thumbnail = fields.TextField(blank=True, null=True)
    library_id = fields.TextField(null=True, blank=True)
    video_id = fields.TextField(null=True, blank=True)
    video_duration = fields.FloatField(blank=True, null=True)
    video_360 = fields.TextField(null=True, blank=True)
    video_size_360 = fields.IntField(null=True, blank=True)
    video_540 = fields.TextField(null=True, blank=True)
    video_size_540 = fields.IntField(null=True, blank=True)
    video_720 = fields.TextField(null=True, blank=True)
    video_size_720 = fields.IntField(null=True, blank=True)
    category_topic = fields.ForeignKeyField(
        "models.CategoryTopics", related_name="CategoryLectures", on_delete='CASCADE', index=True
    )
    discription = fields.TextField(blank=True, null=True)
    order_display = fields.IntField(default=0)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
