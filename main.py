import uvicorn
from fastapi import Body, FastAPI, Request, Response
from typing import Callable, List
from fastapi.routing import APIRoute
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_limiter.depends import RateLimiter
from fastapi_limiter import FastAPILimiter
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
from starlette_session import SessionMiddleware
from tortoise.contrib.fastapi import register_tortoise

from admin_dashboard import controller as adminController
from apis import routes as apiController
# from checkout import controller as checkoutController
from configs import appinfo
from configs.connection import DATABASE_URL, database
from courses import controller as courseController
from scholarship_tests import controller as scholarshipController
from send_mails import controller as mailController
from student import controller as studentController
from study_material import controller as studyMaterialController
from starlette_context import middleware, plugins


session = None
# redis_client = Redis(host="localhost", port=6379)


# logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

# logger = logging.getLogger(__name__)

# logging.basicConfig(filename='error.log', encoding='utf-8', level=logging.DEBUG)
# logging.debug('This message should go to the log file')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')


@lru_cache()
def app_setting():
    return appinfo.Setting()


settings = app_setting()

fastapi_params = settings.debug

allowed_host = settings.allowed_host

if fastapi_params == 'True':
    app = FastAPI(debug=True)
    LOCAL_REDIS_URL = "redis://localhost"


else:
    app = FastAPI(debug=False, docs_url=None, redoc_url=None, openapi_url=None)
    LOCAL_REDIS_URL = "redis://imagnuscache-001.8vqeqj.0001.aps1.cache.amazonaws.com"

#    app.add_middleware(HTTPSRedirectMiddleware)
#    while(True):
#      print("infinite loop")
config = Config(".env")


class GzipRequest(Request):
    async def body(self) -> bytes:
        if not hasattr(self, "_body"):
            body = await super().body()
            if "gzip" in self.headers.getlist("Content-Encoding"):
                body = gzip.decompress(body)
            self._body = body
        return self._body


class GzipRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            request = GzipRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler


app.router.route_class = GzipRoute


app.add_middleware(
    middleware.ContextMiddleware,
    plugins=(
        plugins.ForwardedForPlugin(),
    ),
)
app.add_middleware(GZipMiddleware)


app.mount("/static", StaticFiles(directory="static"), name="static")

# app.add_middleware(HTTPSRedirectMiddleware)

'''

#add docs behind the authentication


security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "user")
    correct_password = secrets.compare_digest(credentials.password, "password")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/docs")
async def get_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


@app.get("/openapi.json")
async def openapi(username: str = Depends(get_current_username)):
    return get_openapi(title = "FastAPI", version="0.1.0", routes=app.routes)





'''


# print(hosts)

origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:8080",
]

# app.add_middleware(
#     TrustedHostMiddleware, allowed_hosts=[
#         "127.0.0.1", "*.imagnus.in"]
# )


app.add_middleware(SessionMiddleware, secret_key="secret",
                   cookie_name="cookie22")

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.get("/app/info", tags=["App"])
# async def app_info(setting: appinfo.Setting = Depends(app_setting)):
#     return {
#         "app_name": setting.app_name,
#         "app_version": setting.app_version,
#         "app_framework": setting.app_framework,
#         "app_date": setting.app_date,
#     }


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
    # logger.info(f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}")

    return response


@cache()
async def get_cache():
    return 1


@app.on_event("startup")
async def startup():
    global session
    # session = aiohttp.ClientSession()
    # # redis_cache = FastApiRedisCache()
    # # redis_cache.init(
    # #     host_url=os.environ.get("REDIS_URL", LOCAL_REDIS_URL),
    # #     prefix=None,
    # #     response_header="X-MyAPI-Cache",
    # #     ignore_arg_types=[Request, Response, Session]
    # # )
    # await FastAPILimiter.init(redis)
    # redis = aioredis.from_url(
    #     LOCAL_REDIS_URL, encoding="utf8", decode_responses=True)
    # FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    # await database.connect()


@app.on_event("shutdown")
async def shutdown():
    # await session.close()
    await database.disconnect()


@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    # Change here to LOGGER
    return JSONResponse(status_code=208, content={"message": f"{base_error_message}. Detail: {err}"})


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


db_url = DATABASE_URL()


# async def run():
#     await Tortoise.init(
#         {

#             "app": app,
#             "connections": {
#                 "default": {
#                     "engine": "tortoise.backends.asyncpg",
#                     "credentials": {
#                         "host": settings.db_host,
#                         "port": "5432",
#                         "user": settings.db_username,
#                         "password": settings.db_password,
#                         "database": settings.db_database,
#                     },
#                 }
#             },
#             "apps": {"models": {"models": [
#                 'admin_dashboard.models',
#                 'student.models',
#                 "student_choices.models",
#                 "screen_banners.models",
#                 "checkout.models",
#                 "send_mails.models",
#                 "study_material.models",
#                 "scholarship_tests.models",
#             ],


#                 "default_connection": "default"}},
#             'use_tz': True,
#             'timezone': 'Asia/Kolkata'
#         },
#         _create_db=True,
#     )
#     await Tortoise.generate_schemas()


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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
