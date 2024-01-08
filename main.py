import traceback
import uvicorn
from hypercorn.config import Config
from hypercorn.asyncio import serve
from fastapi import status, FastAPI, Request, Response, HTTPException
from starlette.responses import JSONResponse, Response, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Callable, List
from fastapi.routing import APIRoute
from fastapi_limiter.depends import RateLimiter
from fastapi_limiter import FastAPILimiter
from admin_dashboard.apis.route import update_video_links
# import aioredis
from scholarship_tests.apis import route as scholarshipRoute
import random
import string
import time
from functools import lru_cache
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from tortoise import Tortoise, fields, run_async
import gzip
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime, timezone
from tortoise.contrib.fastapi import register_tortoise
from admin_dashboard import controller as adminController
from apis import routes as apiController
from configs import appinfo
from configs.connection import DATABASE_URL, database
from courses import controller as courseController
from scholarship_tests import controller as scholarshipController
from send_mails import controller as mailController
from student import controller as studentController
from student.apis.route import download_videos
from student.models import UserToken
from study_material import controller as studyMaterialController
from starlette_context import middleware, plugins
# from mangum import Mangum
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
import requests
from middlewares.TokenValidationMiddleware import TokenValidationMiddleware
import httpx
from contextlib import asynccontextmanager
from fastapi.exceptions import HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import json



limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()

debug_mode = settings.debug

SLACK_WEBHOOK_URL = settings.slack_webhook_url

class SlackHandler(logging.Handler):
     def emit(self, record):
        log_entry = self.format(record)
        payload = {
            "text": f"```{log_entry}```",
        }
        httpx.post(SLACK_WEBHOOK_URL, json=payload)
        




session = None





allowed_host = settings.allowed_host



logger = logging.getLogger("fastapi")
logger.setLevel(logging.INFO)
slack_handler = SlackHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
slack_handler.setFormatter(formatter)
logger.addHandler(slack_handler)



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
   
    print(debug_mode)
    yield
    # Shutdown logic
    print("Shutting down")


if debug_mode == 'True':
    print('yes')
    app = FastAPI()
    LOCAL_REDIS_URL = "redis://localhost"


else:
    app = FastAPI(debug=False, docs_url=None, redoc_url=None, openapi_url=None)
    LOCAL_REDIS_URL = "redis://imagnuscache-001.8vqeqj.0001.aps1.cache.amazonaws.com"


app.lifespan = lifespan  # Assign the lifespan function

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Construct a log entry as a dictionary
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": "ERROR",
        "APP_TYPE": "TEST",
        "message": "An error occurred",
        "api_endpoint": request.url.path,
        "http_method": request.method,
        "error": str(exc),
    }

    # Log the structured error message with pretty print
    formatted_log = json.dumps(log_entry, indent=2)
    logger.error(formatted_log)

    # Print the error for debugging (optional)
    # print(formatted_log)

    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )
  



app.add_middleware(SessionMiddleware, secret_key="secret")

secret_key = settings.secret_key.encode('utf-8')


class GzipRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            if "gzip" in self.headers.getlist("Content-Encoding"):
                body = gzip.decompress(body)
            self._body = body
        return self._body


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    idem = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    # logger.info(f"rid={idem} start request path={request.url.path}")
    start_time = time.time()
    response = await call_next(request)
    end_time = time.time()
    process_time = (end_time - start_time)
    response.headers['X-Process-Time'] = str(process_time)
    formatted_process_time = '{0:.2f}'.format(process_time)
    return response




# app.add_middleware(TokenValidationMiddleware)


@app.get("/error")
async def raise_error():    
  exc = Exception("Something went wrong!")  

  logger.error(f"An error occurred: {exc}")
    
  raise Exception("Something went wrong!")


app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# app.include_router(authController.router, tags=["Auth"])
app.include_router(apiController.api_router, prefix="/api", tags=["APIs"])
app.include_router(scholarshipRoute.router, tags=['Scholarship APIs'])
# app.include_router(checkoutController.router, tags=["checkout"])
app.include_router(adminController.router, tags=["Admin"])
app.include_router(studentController.router, tags=["Students"])
app.include_router(courseController.router, tags=["Courses"])
app.include_router(mailController.router, tags=["Mailer"])
app.include_router(studyMaterialController.router)
app.include_router(scholarshipController.router)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


  

db_url = DATABASE_URL()


register_tortoise(
    app=app,
    config={
        'connections': {
            'default': db_url
        },
        'apps': {
            'models': {
                'models': [
                    'admin_dashboard.models',
                    'student.models',
                    "student_choices.models",
                    "screen_banners.models",
                    "checkout.models",
                    "send_mails.models",
                    "study_material.models",
                    "scholarship_tests.models",
                ],
                # If no default_connection specified, defaults to 'default'
                'default_connection': 'default',
            }
        },
        'use_tz': True,
        'timezone': 'Asia/Kolkata'
    },
    generate_schemas=True,
    add_exception_handlers=True,
)


# if __name__ == "__main__":
#     run_async(run())


