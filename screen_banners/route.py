from typing import List

from fastapi import APIRouter, Depends
from imagekitio import ImageKit
from pydantic import BaseModel
from tortoise.contrib.fastapi import HTTPNotFoundError

from aws_services.settings import settings
from screen_banners.models import ScreenBanners, ScreenBanners_Pydantic
from utils.util import get_current_user
from student.apis.route import manager 
router = APIRouter()


class Status(BaseModel):
    message: str


imagekit = ImageKit(
    private_key=settings.IMAGEKIT_PRIVATE_KEY,
    public_key=settings.IMAGEKIT_PUBLIC_KEY,
    url_endpoint='https://ik.imagekit.io/imagnus/'
)


# @router.post('/add_screen_banners', )
# async def add_banners(s3: BaseClient = Depends(s3_auth),
#                       name: str = Form(...), image: UploadFile = File(...)):
#     folder = 'screen_banners'
#     upload_obj = upload_file_to_bucket(s3_client=s3, file_obj=image.file,
#                                        bucket='testing-bucket-s3-uploader',
#                                        folder=folder,
#                                        object_name=image.filename
#                                        )
#     if upload_obj:
#         imagekit_url = imagekit.url({
#             "path": "/" + folder + "/" + image.filename,
#             "url_endpoint": "https://ik.imagekit.io/imagnus/",
#             # "transformation": [{"height": "300", "width": "400"}],
#         })
#
#         await ScreenBanners.create(name=name, image_url=imagekit_url)
#
#     return Status(message="New Image added successfully")


@router.get('/screen_images/', response_model=List[ScreenBanners_Pydantic],
            responses={404: {"model": HTTPNotFoundError}})
async def get_screen_images(_=Depends(manager)):
    return await ScreenBanners_Pydantic.from_queryset(ScreenBanners.filter(is_active=True))
