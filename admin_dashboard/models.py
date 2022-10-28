from enum import IntEnum
from tortoise import Tortoise
from tortoise import fields
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.models import Model


class Admin(Model):
    id = fields.UUIDField(pk=True)
    mobile = fields.CharField(max_length=10, unique=True)
    password = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)


class AccessToAdminArea(Model):
    id = fields.UUIDField(pk=True)
    is_enabled = fields.BooleanField(default=True)
    allowed_users = fields.IntField(default=1)
    current_users = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True)


class AdminLoginTracker(Model):
    id = fields.UUIDField(pk=True)
    ip = fields.CharField(max_length=42, unique=True)
    allowed_users = fields.IntField()
    current_users = fields.IntField()
    identity = fields.TextField(blank=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Preference(Model):
    """
    This references a Tournament
    """

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    slug = fields.CharField(max_length=250, unique=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "preference"

    def __str__(self):
        return self.name


class Course(Model):
    """
    This references an Event in a Tournament
    """
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    slug = fields.CharField(max_length=250, unique=True)
    icon_image = fields.TextField()
    description = fields.TextField(null=True, blank=True)
    web_icon = fields.TextField(null=True, blank=True)
    telegram_link = fields.TextField(null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    preference = fields.ForeignKeyField(
        "models.Preference", related_name="courses", on_delete='CASCADE',
    )


class Category(Model):
    """
    This references a Category Table
    """

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    slug = fields.CharField(max_length=150, unique=True)
    icon_image = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(null=True, blank=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "category"

    def __str__(self):
        return self.name


class CourseCategories(Model):
    id = fields.UUIDField(pk=True)
    category = fields.ForeignKeyField(
        "models.Category", related_name="course_categories", on_delete='CASCADE',
    )
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    course = fields.ForeignKeyField(
        "models.Course", related_name="categories", on_delete='CASCADE',
    )
    is_free = fields.BooleanField(default=False)
    # class PydanticMeta:
    #     exclude = ["category", "is_active", "updated_at", "created_at"]


class subjects(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=250, unique=True)
    slug = fields.CharField(max_length=150, unique=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CategorySubjects(Model):
    id = fields.UUIDField(pk=True)
    subject = fields.ForeignKeyField(
        "models.subjects", related_name="subjects_CategorySubjects", on_delete='CASCADE',
    )
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    category = fields.ForeignKeyField(
        "models.Category", related_name="category_CategorySubjects", on_delete='CASCADE',
    )


class Topics(Model):
    """
    This references a chapters
    """
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=250, )
    slug = fields.CharField(max_length=150)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    category = fields.ForeignKeyField(
        "models.Category", related_name="topics", on_delete='CASCADE',
    )


class CategoryTopics(Model):
    """
    This references a category chapters
    """

    id = fields.UUIDField(pk=True, index=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    order_seq = fields.IntField(default=0, index=True)
    category = fields.ForeignKeyField(
        "models.CourseCategories", related_name="categories_topics", on_delete='CASCADE', index=True
    )
    topic = fields.ForeignKeyField(
        "models.Topics", related_name="categories_topics_title", on_delete='CASCADE', index=True
    )


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
    category_topic = fields.ForeignKeyField(
        "models.CategoryTopics", related_name="CategoryLectures", on_delete='CASCADE', index=True
    )
    discription = fields.TextField(blank=True, null=True)
    order_display = fields.IntField(default=0)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CourseCategoryNotes(Model):
    id = fields.UUIDField(pk=True, index=True)
    title = fields.CharField(max_length=250, null=True, blank=True)
    slug = fields.CharField(max_length=550, null=True, blank=True)
    notes_url = fields.TextField()
    thumbnail = fields.TextField(null=True, blank=True)
    category_topic = fields.ForeignKeyField(
        "models.CategoryTopics", related_name="CategoryNotes", on_delete='CASCADE', index=True
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CourseCategoryTestSeries(Model):
    id = fields.UUIDField(pk=True, index=True)
    category_topic = fields.ForeignKeyField(
        "models.CategoryTopics", related_name="CategoryTestSeries", on_delete='CASCADE', index=True
    )
    series_no = fields.IntField(blank=True, null=True)
    time_duration = fields.IntField()
    marks = fields.IntField()
    no_of_qstns = fields.IntField()
    title = fields.CharField(max_length=50, null=True, blank=True)
    description = fields.TextField(null=True, blank=True)
    thumbnail = fields.TextField(null=True, blank=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CourseCategoryTestSeriesQuestions(Model):
    id = fields.UUIDField(pk=True, index=True)
    question = fields.TextField()
    opt_1 = fields.TextField()
    opt_2 = fields.TextField()
    opt_3 = fields.TextField()
    opt_4 = fields.TextField()
    answer = fields.CharField(max_length=10)
    solution = fields.TextField()
    test_series = fields.ForeignKeyField(
        "models.CourseCategoryTestSeries", related_name="CategoryTestSeriesQuestions", on_delete='CASCADE', index=True
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CourseCategoryOverview(Model):
    id = fields.UUIDField(pk=True)
    overview = fields.TextField()
    examination = fields.TextField()
    syllabus = fields.TextField()
    course = fields.ForeignKeyField(
        "models.Course", related_name="course_overview", on_delete='CASCADE',
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class Instructor(Model):
    """
    This references a instructor Table
    """

    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    slug = fields.CharField(max_length=150, unique=True)
    yoe = fields.DateField(null=True)
    image_url = fields.TextField(null=True)
    bio = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class SubscriptionPlans(Model):
    id = fields.UUIDField(pk=True, index=True)
    name = fields.CharField(max_length=50)
    slug = fields.CharField(max_length=60)
    sub_title = fields.CharField(max_length=50)
    icon_image = fields.TextField()
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CourseSubscriptionPlans(Model):
    id = fields.UUIDField(pk=True)
    course = fields.ForeignKeyField(
        "models.Course", related_name="CourseSubscriptionPlans_course", on_delete='CASCADE', index=True
    )

    SubscriptionPlan = fields.ForeignKeyField(
        "models.SubscriptionPlans", related_name="SubscriptionPlans", on_delete='CASCADE', index=True
    )
    validity = fields.IntField(blank=True, null=True)
    plan_price = fields.IntField(default=0)
    discount_price = fields.IntField(default=0)
    no_of_videos = fields.IntField(default=0)
    no_of_notes = fields.IntField(default=0)
    no_of_tests = fields.IntField(default=0)
    live_classes_access = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    plan_features = fields.TextField(blank=True, null=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class LiveClasses(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=250)
    course = fields.ForeignKeyField(
        "models.Course", related_name="liveClasses_course", on_delete='CASCADE', index=True
    )
    lecture = fields.ForeignKeyField(
        "models.CourseCategoryLectures", related_name="live_lectures", on_delete='CASCADE', index=True
    )
    instructor = fields.ForeignKeyField(
        "models.Instructor", related_name="live_lecture_Instructor", on_delete='CASCADE', index=True
    )
    url = fields.TextField(blank=True, null=True)
    is_paid = fields.BooleanField(default=False)
    thumbnail = fields.TextField(null=True, blank=True)
    streaming_time = fields.DatetimeField()
    lecture_duration = fields.CharField(max_length=40, blank=True, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class addAppStaticUrls(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=100)
    url = fields.TextField(null=True, blank=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class offerBanners(Model):
    id = fields.UUIDField(pk=True)
    title = fields.CharField(max_length=100)
    url = fields.TextField(null=True, blank=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CouponType(IntEnum):
    percentage = 1
    flat = 2


class ApplyMode(IntEnum):
    first_time = 1
    on_all = 2


class Coupons(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(80)
    discount = fields.IntField()
    subscription = fields.ForeignKeyField(
        "models.CourseSubscriptionPlans", related_name="student_coupon_subscription", on_delete='CASCADE', index=True
    )
    coupon_type = fields.IntEnumField(
        CouponType, default=CouponType.percentage)
    apply_mode = fields.IntEnumField(
        ApplyMode, default=ApplyMode.on_all)
    discription = fields.TextField(blank=True, null=True)
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CourseCart(Model):
    id = fields.UUIDField(pk=True)
    student = fields.ForeignKeyField(
        "models.Student", related_name="student_cart", on_delete='CASCADE', index=True
    )
    subscription = fields.ForeignKeyField(
        "models.CourseSubscriptionPlans", related_name="student_cart_subscription", on_delete='CASCADE', index=True
    )
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now=True)


class TestType(IntEnum):
    PRE = 1
    MAINS = 2


class Scholarship2021(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(250)
    email = fields.CharField(150, unique=True)
    mobile = fields.CharField(10, unique=True)
    exam_type = fields.IntEnumField(TestType, default=TestType.PRE)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class InterViewProgram(Model):
    name = fields.CharField(150)
    email = fields.CharField(150, unique=True)
    mobile = fields.CharField(10, unique=True)
    roll_no = fields.CharField(20, unique=True)
    file = fields.TextField()
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)


class CurrentAffairs(Model):
    day = fields.CharField(2)
    month_year = fields.CharField(30)
    file_url = fields.TextField()
    is_active = fields.BooleanField(default=True)
    updated_at = fields.DatetimeField(auto_now=True)
    created_at = fields.DatetimeField(auto_now_add=True)

Tortoise.init_models(["admin_dashboard.models", "student.models", ], "models")
Preference_Pydantic = pydantic_model_creator(Preference)
PreferenceIn_Pydantic = pydantic_model_creator(
    Preference, name="PreferenceIn", exclude_readonly=True)
Course_Pydantic = pydantic_model_creator(Course)
CourseIn_Pydantic = pydantic_model_creator(
    Course, name="CourseIn", exclude_readonly=True)
CategoryIn_Pydantic = pydantic_model_creator(
    CourseCategories, name="CategoryIn", exclude_readonly=True)
CourseCategories_Pydantic = pydantic_model_creator(CourseCategories)
Category_Pydantic = pydantic_model_creator(Category)
CourseCategoriesIn_Pydantic = pydantic_model_creator(
    CourseCategories, name="CategoryIn", exclude_readonly=True)
CategorySubjectsIn_Pydantic = pydantic_model_creator(
    CategorySubjects, name="CategorySubjectsIn", exclude_readonly=True)
CategorySubjects_Pydantic = pydantic_model_creator(CategorySubjects)
subjects_Pydantic = pydantic_model_creator(subjects)
Topics_Pydantic = pydantic_model_creator(Topics)
CategoryTopics_Pydantic = pydantic_model_creator(CategoryTopics)
CourseCategoryLectures_Pydantic = pydantic_model_creator(
    CourseCategoryLectures)
CourseCategoryNotes_Pydantic = pydantic_model_creator(CourseCategoryNotes)
CourseCategoryTestSeries_Pydantic = pydantic_model_creator(
    CourseCategoryTestSeries)
CourseCategoryTestSeriesQuestions_Pydantic = pydantic_model_creator(
    CourseCategoryTestSeriesQuestions)
CourseCategoryOverview_Pydantic = pydantic_model_creator(
    CourseCategoryOverview)
Instructor_Pydantic = pydantic_model_creator(Instructor)
InstructorIn_Pydantic = pydantic_model_creator(
    Instructor, name="InstructorIn", exclude_readonly=True)
SubscriptionPlans_Pydantic = pydantic_model_creator(SubscriptionPlans)
CourseSubscriptionPlans_Pydantic = pydantic_model_creator(
    CourseSubscriptionPlans)
LiveClassesIn_Pydantic = pydantic_model_creator(
    LiveClasses, name="LiveClassesIn", exclude_readonly=True)
LiveClasses_Pydantic = pydantic_model_creator(LiveClasses)
addAppStaticUrls_Pydantic = pydantic_model_creator(addAppStaticUrls)
offerBanners_Pydantic = pydantic_model_creator(offerBanners)
CourseCartIn_Pydantic = pydantic_model_creator(
    CourseCart, name="CourseCartIn", exclude_readonly=True)
CourseCart_Pydantic = pydantic_model_creator(CourseCart)
CurrentAffairs_Pydantic = pydantic_model_creator(CurrentAffairs)
