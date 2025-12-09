
from tortoise import Tortoise, fields, run_async
from fastapi import Body, FastAPI, Request, Response
from controller import download_videos
from configs.connection import DATABASE_URL

db_url = DATABASE_URL()


app = FastAPI()

@app.on_event("startup")
async def startup():

    await Tortoise.init(
        db_url=db_url,
        modules={'models': [
            'admin_dashboard.models',
            'student.models',
            "student_choices.models",
            "screen_banners.models",
            "checkout.models",
            "send_mails.models",
            "study_material.models",
            "scholarship_tests.models",

        ]}
    )
    await Tortoise.generate_schemas()

    await download_videos()
