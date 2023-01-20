import os
import time
from celery import Celery
import aiofiles
from fastapi import UploadFile
import boto3
import pathlib
import ffmpeg
from fastapi.encoders import jsonable_encoder
import requests
import json


ACCESS_KEY = 'AKIAWSYDR36FQBPK43DS'
SECRET_KEY = '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'

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get(
    "CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379")


@celery.task(name="create_task")
async def create_task(video_file):
    async with aiofiles.open(video_file.filename, 'wb') as f:
        while contents := await video_file.read(1024 * 1024):
             await f.write(contents)
        print("Created video file")
        return True


def upload_to_aws(s3_file):
   try:
       s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                         aws_secret_access_key=SECRET_KEY)

       file_name = os.path.join(pathlib.Path(
           __file__).parent.resolve(), s3_file)
       file_name = s3_file
       with open(file_name, "rb") as data:
           s3.upload_fileobj(
               data, "testing-bucket-s3-uploader",
               s3_file
           )
   except Exception as e:
       print(str(e))
       return {"message": str(e)}


@celery.task(name="read_upload_video_lecture")
def read_upload_video_lecture(video_file, id):

       try:

            print("REACHED HERE")
            aud = ffmpeg.input(video_file.filename).audio

            def make_variant(px):
                print("LOOP"+str(px))

                vid = ffmpeg.input(
                    video_file.filename).video.filter('scale', -1, px)

                if not os.path.exists("transcoded/"+video_file.filename):
                    os.makedirs("transcoded/"+video_file.filename)

                if os.path.exists("transcoded/"+video_file.filename+"/"+str(px)+".mp4"):
                    os.remove("transcoded/"+video_file.filename +
                              "/"+str(px)+".mp4")

                out = ffmpeg.output(vid, aud, "transcoded/" +
                                    video_file.filename+"/"+str(px)+".mp4")
                out.run()
                return "transcoded/"+video_file.filename+"/"+str(px)+".mp4"

            file_360 = make_variant(360)
            file_540 = make_variant(540)
            file_720 = make_variant(720)
            file_360_size = os.path.getsize(file_360)
            file_540_size = os.path.getsize(file_540)
            file_720_size = os.path.getsize(file_720)

            url = "https://testserver.imagnus.in/update/video/size"
            headers = {'accept': 'application/json',
                'Content-Type': 'application/json'}
            data = {
                "id": jsonable_encoder(id),
                "size_360": file_360_size,
                "size_540": file_540_size,
                "size_720": file_720_size
            }
            print(data)
            response = requests.post(
                url, headers=headers, data=json.dumps(data))
            print(response.status_code)
            print(response.text)

            upload_to_aws(file_360)
            print("360PX uploaded")

            os.remove(file_360)
            upload_to_aws(file_540)
            print("540PX uploaded")
            os.remove(file_540)
            upload_to_aws(file_720)
            print("720PX uploaded")
            os.remove(file_720)
            os.remove(video_file.filename)
            os.remove("transcoded/"+video_file.filename+"/")

            return {'status': True, 'video_variants': {'360': file_360, '540': file_540, '720': file_720}}
       except Exception as e:
            return {"error": str(e)}
